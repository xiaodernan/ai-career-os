"""docs/QUALITY_GATES.md must exist as a factual gate index.

The project has many contract/security/deploy gates; an index helps maintainers
discover and run them. This gate checks existence and key sections (not counts).
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs" / "QUALITY_GATES.md"


def test_quality_gates_doc_has_required_structure() -> None:
    assert DOC.is_file(), "docs/QUALITY_GATES.md missing"
    text = DOC.read_text(encoding="utf-8")
    assert len(text) >= 1200
    for marker in (
        "# Quality Gates",
        "## How to run",
        "pytest",
        "vitest",
        "mvn",
        "## Gate categories",
        "Security",
        "## Rules for adding gates",
        "destructive proof",
        "explicit paths",
    ):
        assert marker in text, f"QUALITY_GATES.md missing marker: {marker!r}"
