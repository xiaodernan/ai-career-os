"""ROADMAP's epic ledger names each epic exactly once.

The file is the standing backlog; an epic's section is its ledger entry,
not a comment. On 2026-11-08 the Epic 73 section had been inserted twice
by the pass that created it -- once between Epics 32 and 33, once after
Epic 70's checklist -- and the two copies disagreed on the marker
("planning" vs "in progress"). Neither copy was wrong on its own; the
duplicate was the defect, and only a count catches it. Epic 72's entry
was missing from the same ledger because its heading had no `##` prefix
while every other epic's did -- a heading the walk cannot see is an
entry that does not exist.

The gate reads every `## Epic N` heading and asserts:

* each epic number from 10 to 73 (the recorded floor) appears exactly once;
* no epic number -- including ones beyond the floor -- appears twice;
* the walk reads at least the floor's worth of headings, so the gate
  cannot go vacuous by matching nothing.

The range is a floor, never a ceiling: a concurrent session landing
Epic 74 keeps this green.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ROADMAP = ROOT / "docs" / "ROADMAP.md"

HEADING = re.compile(r"^## Epic (\d+)\b", re.M)
FLOOR = 10
CEILING = 73  # the last recorded epic; the gate's floor, not a limit on the file


def _headings() -> list[int]:
    text = ROADMAP.read_text(encoding="utf-8", errors="replace")
    return [int(m.group(1)) for m in HEADING.finditer(text)]


def test_every_recorded_epic_has_exactly_one_heading():
    headings = _headings()
    for n in range(FLOOR, CEILING + 1):
        assert headings.count(n) == 1, (
            f"Epic {n} appears {headings.count(n)} times in docs/ROADMAP.md -- "
            "the epic's section is its ledger entry; give it one home and delete the other copies")


def test_no_epic_heading_is_written_twice():
    headings = _headings()
    duplicates = sorted({n for n in headings if headings.count(n) > 1})
    assert duplicates == [], (
        f"{duplicates}: an epic heading appears more than once -- "
        "an Epic-73-style double insertion is exactly what this pins")


def test_the_walk_is_not_vacuous():
    headings = _headings()
    assert len(headings) >= CEILING - FLOOR + 1, (
        f"only {len(headings)} epic headings found -- the reader narrowed or the "
        "heading convention changed; a gate that reads nothing passes everything")
