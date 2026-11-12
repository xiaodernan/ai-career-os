"""The process-wide outbound HTTP pool has an explicit, measured contract (Epic 157).

``registry._http_client()`` is a module-level ``@lru_cache`` client shared by every LLM,
embedding and voice provider for the whole life of the process. It is the most expensive and
most reused network boundary in the service, yet before this change its ``limits`` were an
invisible httpx-version default: a dependency bump could silently change the production
concurrency ceiling and persistent-connection reuse with no diff in our code. The fix declares those
limits explicitly, at the values httpx 0.28.1 already applies, so declaring them is
byte-for-byte behaviour-preserving while turning a silent default into an auditable contract.

The client-level ``timeout`` is deliberately left at httpx's default. Every provider call
passes its own per-request timeout matched to its latency (60s embeddings up to 600s ollama
streams), which a client-level value would only shadow; setting one here would be a dead
config that misleads the next maintainer into believing it bounds a long generation. The
real risk this file closes is the opposite: a *future* provider that forgets to pass a
timeout would silently inherit httpx's 5s default and abort a long model call. So the second
half of the contract pins that every outbound call still carries its own timeout — the
fragile premise that makes "leave the client default alone" correct.

Offline and source-only: it builds no provider, opens no socket and needs no key. The one
client it inspects is a fresh ``AsyncClient`` with the declared limits, never the cached
singleton, so this test cannot bind ``_http_client``'s cached connection pool to the test
event loop (the trap Epic 155/156 record).
"""

from __future__ import annotations

import re
from pathlib import Path

import httpx

from app.providers import registry

APP_ROOT = Path(__file__).resolve().parents[1] / "app"

# httpx 0.28.1's actual runtime defaults, measured in this environment before declaring
# them: pool max_connections=100, max_keepalive_connections=20. Pinning these values means a
# dependency upgrade that changes either default reddens this file instead of quietly
# changing production throughput.
EXPECTED_MAX_CONNECTIONS = 100
EXPECTED_MAX_KEEPALIVE = 20


def test_the_shared_limits_are_the_measured_defaults():
    """Declaring the contract must not move it: same numbers httpx already used."""
    assert registry._SHARED_LIMITS.max_connections == EXPECTED_MAX_CONNECTIONS
    assert registry._SHARED_LIMITS.max_keepalive_connections == EXPECTED_MAX_KEEPALIVE


def test_the_client_actually_applies_them():
    """The declared limits reach the connection pool, not just a module constant.

    A fresh client with the same limits is used on purpose: reading the cached singleton
    here would bind its pool to this test's event loop and break the live-provider tests
    that reuse it later in the same process.
    """
    client = httpx.AsyncClient(limits=registry._SHARED_LIMITS)
    try:
        pool = client._transport._pool  # httpx 0.28.1 keeps limits on the pool
        assert pool._max_connections == EXPECTED_MAX_CONNECTIONS
        assert pool._max_keepalive_connections == EXPECTED_MAX_KEEPALIVE
    finally:
        # no `await` needed: no connection was ever opened, so there is nothing to drain
        pass


def test_the_factory_builds_its_client_with_the_declared_limits():
    """Source contract: ``_http_client`` cannot drift back to a bare ``AsyncClient()``."""
    source = (APP_ROOT / "providers" / "registry.py").read_text(encoding="utf-8")
    m = re.search(r"def _http_client\([^)]*\)[^\n]*:\s*\n\s*return\s+([^\n]+)", source)
    assert m, "the _http_client factory body could not be read"
    assert "_SHARED_LIMITS" in m.group(1), (
        f"_http_client builds its client without the declared limits: {m.group(1)!r}; "
        "the pool contract must be applied at construction, not merely declared nearby")


def test_every_provider_outbound_call_still_passes_its_own_timeout():
    """The zero-drift premise: no call may inherit the client's 5s default.

    The shared client keeps httpx's default timeout on purpose. That is only safe while
    every call overrides it. This scans each provider's outbound call site and requires a
    ``timeout=`` in the call's own argument list (across the line break httpx calls use),
    so adding a provider that forgets it reddens this gate instead of silently capping a
    long generation at 5 seconds.
    """
    provider_files = sorted((APP_ROOT / "providers" / "llm").glob("*.py")) + sorted(
        (APP_ROOT / "providers" / "voice").glob("*.py"))
    checked = 0
    for path in provider_files:
        text = path.read_text(encoding="utf-8")
        # Only the shared client's outbound calls count. Matching a bare `.get(` would
        # sweep up every `dict.get(...)` in the provider and flag a dictionary lookup as
        # a network call; `self.client.` is the seam `registry` injects, so it is the exact
        # population whose timeout matters.
        for m in re.finditer(r"self\.client\.((?:post|stream|get|put|patch))\(", text):
            # Walk to the matching ')' so a timeout on a later line still counts.
            start = m.end() - 1
            depth = 0
            end = start
            for i in range(start, len(text)):
                if text[i] == "(":
                    depth += 1
                elif text[i] == ")":
                    depth -= 1
                    if depth == 0:
                        end = i
                        break
            call = text[start:end + 1]
            assert re.search(r"\btimeout\s*=", call), (
                f"{path.relative_to(APP_ROOT.parent)}: a '.{m.group(1)}(' outbound call has "
                "no per-request timeout; it would inherit the shared client's 5s default "
                "and could abort a long model call. Pass an explicit timeout.")
            checked += 1
    assert checked >= 10, (
        f"only {checked} provider outbound calls were found; the walk likely narrowed and "
        "this gate must not pass vacuously")
