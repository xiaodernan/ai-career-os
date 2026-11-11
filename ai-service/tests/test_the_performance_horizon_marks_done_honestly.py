"""The performance horizon never claims a ship it cannot name.

``docs/plans/PERFORMANCE_HORIZON.md`` is the standing ledger for the
118-124 horizon. Two ways a ledger like that goes rotten without a gate:

* an epic gets marked ``DONE`` without a date, and "verified" becomes a
  vibe instead of a measurement;
* an epic gets marked ``DONE`` in the horizon but never lands in
  ``docs/ROADMAP.md``'s checklist, so the two ledgers disagree and neither
  reader can trust the other.

The horizon's own rules (stated at the top of the file) say every number
is a measurement and every claim gets pinned. This gate enforces the
part that can be checked from the two files alone: DONE means a dated
verification line, and DONE means the roadmap checklist says so too.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HORIZON = ROOT / "docs" / "plans" / "PERFORMANCE_HORIZON.md"
ROADMAP = ROOT / "docs" / "ROADMAP.md"

SECTION = re.compile(r"^## Epic (\d+)[^\n]*$", re.M)
HORIZON_EPICS = range(118, 128)  # the horizon covers 118..127


def _sections():
    text = HORIZON.read_text(encoding="utf-8", errors="replace")
    marks = list(SECTION.finditer(text))
    sections = {}
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        sections[int(m.group(1))] = text[m.start():end]
    return sections


def test_the_horizon_carries_every_epic():
    sections = _sections()
    missing = [n for n in HORIZON_EPICS if n not in sections]
    assert missing == [], f"PERFORMANCE_HORIZON.md is missing epic sections: {missing}"


def test_done_means_a_dated_verification():
    sections = _sections()
    undated = []
    for n, body in sections.items():
        head = body.splitlines()[0]
        if "DONE" not in head:
            continue
        if not re.search(r"20\d\d-\d\d-\d\d", body):
            undated.append(n)
    assert undated == [], (
        f"epics {undated} are marked DONE without a date -- a verified claim "
        "names the day it was measured")


def test_done_in_horizon_means_checked_in_roadmap():
    sections = _sections()
    roadmap = ROADMAP.read_text(encoding="utf-8", errors="replace")
    missing = []
    for n, body in sections.items():
        head = body.splitlines()[0]
        if "DONE" not in head:
            continue
        if not re.search(rf"- \[x\] \*\*{n}\*\*", roadmap):
            missing.append(n)
    assert missing == [], (
        f"epics {missing} are DONE in the horizon but unchecked in ROADMAP.md -- "
        "the two ledgers disagree")


def test_the_summary_table_names_each_epic():
    text = HORIZON.read_text(encoding="utf-8", errors="replace")
    table = text.split("| Epic |", 1)[-1].split("## Epic", 1)[0]
    unnamed = [n for n in HORIZON_EPICS if f"| {n} |" not in table]
    assert unnamed == [], f"the horizon's summary table does not name epics {unnamed}"
