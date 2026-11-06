"""71.2 -- every address the browser can build is a row the contract owns.

71.1 walks the backend's routes against the frontend's readers; the public-table
gate walks API.md's §2 rows against the controllers. The third edge was
unmeasured: a path in `endpoints.ts` that the client *can* build but that the
contract never names. Measured at closure (2026-11-07): the whole endpoint map,
**zero undocumented**. So this is a floor with no exemption ledger, not a list of
excuses -- a new key without its row reddens here before a developer has to read
Java to learn what the request takes. The population is held by lower bounds on
both walks rather than a census of key counts: this repo is developed
concurrently, and a pinned count would go stale the moment another session adds
an endpoint (which is exactly what happened while this gate was being written).

Shape *detail* is deliberately not graded here: API.md describes some routes in
prose and others in a row, and the response-shape and public-table gates own
those claims. What this one owns is the address, because a missing address is
the one drift that leaves a client with nothing at all to read.
"""

import re
from pathlib import Path

from tests.test_browser_surface_audit import _endpoint_keys

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs" / "API.md"

# A narrowed parser would clear a zero-missing assertion by reading nothing.
_MIN_CLIENT_PATHS = 100
_MIN_DOCUMENTED_PATHS = 60


def _norm(path: str) -> str:
    """One spelling for an address: params folded, query, hash and base dropped."""
    path = path.split("?")[0].split("#")[0].rstrip("/")
    path = re.sub(r"\$\{[^}]*\}|\{[^}]*\}|\*\*", "{}", path)
    return path.replace("/api/v1", "", 1).strip("/")


def _client_paths() -> set[str]:
    """Addresses the shipped endpoint map can build, from the walk 71.1 owns."""
    return {_norm(t) for t in _endpoint_keys().values() if t.startswith("/")}


def _contract_rows() -> set[str]:
    """Every address API.md writes in a table row, in backticks."""
    out = set()
    text = DOC.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        for match in re.finditer(r"`(/[^`\s]*)`", line):
            out.add(_norm(match.group(1)))
    return out


def test_every_address_the_client_can_build_has_a_row_in_the_contract():
    client, documented = _client_paths(), _contract_rows()
    assert len(client) >= _MIN_CLIENT_PATHS, (
        f"the endpoint-map walk found only {len(client)} paths -- a narrowed parser "
        "would clear this gate by reading nothing")
    assert len(documented) >= _MIN_DOCUMENTED_PATHS, (
        f"the contract walk found only {len(documented)} paths -- the doc reader narrowed")
    missing = sorted(client - documented)
    assert missing == [], (
        f"{missing}: the client can build these addresses but API.md has no row for them. "
        "Document the request and response in the contract, or remove the key -- this gate "
        "keeps no exemption ledger, so a new endpoint cannot arrive undocumented")


def test_the_two_argument_letter_address_is_still_one_the_client_can_build():
    """71.1 lost this key to a parser that could not read a multi-line builder.

    The loss made two served routes look UI-less; it would just as quietly shrink
    the population this gate measures. Pin the address so both walks stay honest.
    """
    assert "applications/{}/letters/{}" in _client_paths(), (
        "the multi-line two-argument builder vanished from the endpoint map again")
    assert "applications/{}/letters/{}" in _contract_rows(), (
        "the letter detail address lost its row in the contract")
