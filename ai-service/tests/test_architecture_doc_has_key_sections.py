"""docs/architecture.md must remain a substantive, structured architecture reference.

This is the primary system-design companion doc linked from README. The gate
checks for core section anchors so accidental truncation or replacement is caught.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs" / "architecture.md"

REQUIRED_MARKERS = (
    "## 1.",
    "## 2.",
    "System topology",
    "## 4.",
    "Data model",
    "## 5.",
    "## 6.",
    "## 8.",
    "Security",
    "## 10.",
)


def test_architecture_doc_exists_and_has_key_sections() -> None:
    assert DOC.is_file(), "docs/architecture.md missing"
    text = DOC.read_text(encoding="utf-8", errors="replace")
    assert len(text) >= 5000, "architecture.md must remain substantive"
    missing = [m for m in REQUIRED_MARKERS if m not in text]
    assert not missing, f"architecture.md missing required markers: {missing}"
