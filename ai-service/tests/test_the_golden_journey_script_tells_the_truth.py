"""The live-stack demo script must not quietly skip stations it claims to cover.

Measured against the running stack on 2026-11-07, `scripts/journey_api.py` printed
`applications: 0` and `bundle sections: []` while ending with `JOURNEY OK — 32
stations`. Both numbers were false and the suite was green:

* A job match does **not** create an application card. The old tracker leg only
  moved a card `if apps["items"]:`, so with an empty pipeline the status move --
  the one part of the journey that exercises the tracker -- never ran, yet the
  script still counted itself as covering §35's loop.
* `call()` already unwraps `{success, data, error}`. Reading
  `(bundle.get("data") or bundle).get("manifest", ...)` reached into the bundle's
  *sections payload* instead of its manifest, so a full 16-section export printed
  an empty section list.

The script's own docstring calls it a regression gate, so a station that never runs
is a gate that proves nothing. Running it needs the live containers; these cases
read the shipped text so the offline suite still catches both shapes coming back.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
JOURNEY = ROOT / "scripts" / "journey_api.py"


def text() -> str:
    return JOURNEY.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")


def test_the_tracker_leg_creates_its_own_card_and_always_moves_it():
    """A guard that can skip the move is the defect, not just a missing assertion."""
    src = text()
    assert re.search(r'^card = call\("create application", "POST", "/applications"', src, re.M), (
        "the journey no longer creates the card it tracks; a match does not create one, "
        "so the tracker leg would be empty again")
    assert re.search(r'^moved = call\("move application", "PATCH", f"/applications/', src, re.M), (
        "the status move is no longer a top-level station -- a guard that skips it leaves "
        "the journey claiming a tracker leg it never walked")
    assert 'assert apps["total"] >= 1' in src, (
        "the journey no longer proves the card it created is in the pipeline")
    assert 'str(moved.get("status", "")).lower() == "applied"' in src, (
        "the status move is no longer asserted, so a no-op PATCH would pass")


def test_the_bundle_manifest_is_read_off_the_value_call_returns():
    """The envelope is unwrapped once, by `call()`; a second unwrap lies about the sections."""
    src = text()
    assert 'return payload.get("data") if not raw else payload' in src, (
        "call() changed its unwrapping: re-read the assertions below against the new shape")
    assert 'bundle.get("manifest", {}).get("counts", {})' in src, (
        "the bundle's manifest is no longer read off the value call() returns")
    assert '(bundle.get("data") or bundle).get("manifest"' not in src, (
        "the export station unwraps the envelope a second time and prints an empty "
        "section list for a bundle that is full")
    assert "assert counts," in src, (
        "the export station no longer proves the bundle names the sections it carries")
