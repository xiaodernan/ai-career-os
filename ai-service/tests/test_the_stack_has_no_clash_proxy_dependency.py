"""The stack goes out on the normal network — no Clash Verge dependency.

For a long time the ai-service container's outbound proxy was written as
``${HTTPS_PROXY:-http://host.docker.internal:7897}``. When the operator's shell
exports the host-local ``HTTP_PROXY=http://127.0.0.1:7897`` (Clash's mixed port),
compose interpolates THAT value into the container — where 127.0.0.1 is the
container itself — and every outbound call dies with ECONNREFUSED. Even with
Clash running, a shell that carries the ambient variable breaks the container.

The fix: the container's proxy knobs are opt-in, separate AI_* variables that
default to empty. This gate keeps the trap from being reintroduced.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
COMPOSE = (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
ENV_EXAMPLE = (REPO_ROOT / ".env.example").read_text(encoding="utf-8")


def _config_lines(text: str) -> list[str]:
    """Non-comment, non-blank lines — a 7897 in an explanatory note is not a binding."""
    return [ln for ln in text.splitlines() if ln.strip() and not ln.lstrip().startswith("#")]


def test_container_proxy_is_opt_in_and_empty_by_default():
    cfg = _config_lines(COMPOSE)
    # The ai-service must not interpolate the ambient host HTTP_PROXY/HTTPS_PROXY.
    assert not any("${HTTPS_PROXY:-" in ln for ln in cfg), "ambient HTTPS_PROXY still leaks into the container"
    assert not any("${HTTP_PROXY:-" in ln for ln in cfg), "ambient HTTP_PROXY still leaks into the container"
    assert not any("7897" in ln for ln in cfg), "a hard-coded Clash port is still bound in the stack"
    # The separate, empty-by-default knobs must be what compose reads.
    assert "HTTPS_PROXY: ${AI_HTTPS_PROXY:-}" in COMPOSE
    assert "HTTP_PROXY: ${AI_HTTP_PROXY:-}" in COMPOSE


def test_env_example_documents_the_direct_default():
    cfg = _config_lines(ENV_EXAMPLE)
    assert any(ln.startswith("AI_HTTPS_PROXY=") and ln.split("=", 1)[1].strip() == "" for ln in cfg)
    assert any(ln.startswith("AI_HTTP_PROXY=") and ln.split("=", 1)[1].strip() == "" for ln in cfg)
    # No active (non-comment) assignment points at the dead Clash port.
    assert not any("7897" in ln for ln in cfg)


def test_internal_fleet_still_bypasses_any_proxy():
    # Whether or not an operator sets a proxy, the internal services stay direct.
    assert "NO_PROXY:" in COMPOSE
    for svc in ("redis", "postgres", "minio", "backend", "gateway", "discovery", "config-server"):
        assert svc in COMPOSE, f"{svc} missing from the fleet bypass"
