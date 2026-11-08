"""The expansion backlog is a tracked planning artifact, not an idea in chat.

`docs/plans/expansion_backlog.md` extends the roadmap beyond 74.x with prioritized,
verifiable epics. This gate ensures the file exists, stays non-trivial, and keeps its
core structure so future sessions can pick work from it deterministically.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKLOG = ROOT / "docs" / "plans" / "expansion_backlog.md"


def test_expansion_backlog_exists_and_has_structure() -> None:
    assert BACKLOG.is_file(), f"missing {BACKLOG}"
    text = BACKLOG.read_text(encoding="utf-8")
    assert len(text) >= 1200, "expansion backlog must be substantive"
    for marker in (
        "# Expansion Backlog",
        "## Status & rules",
        "## P0",
        "## P1",
        "Epic 75",
        "Epic 76",
        "Acceptance",
        "gate",
    ):
        assert marker in text, f"expansion backlog missing required marker: {marker!r}"
    # Epics should be numbered forward from 75 in this backlog.
    ids = [int(m) for m in __import__("re").findall(r"^### Epic (\d+)", text, __import__("re").M)]
    assert ids and ids[0] == 75, f"expected first backlog epic to be 75, got {ids[:3]}"
    assert ids == sorted(ids), f"backlog epic IDs must be ascending: {ids}"
