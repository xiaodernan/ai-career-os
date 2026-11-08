""".gitignore must protect secrets and common build artifacts.

A missing ignore rule for `.env*` (prod secrets) or build outputs causes
accidental commits. This gate checks key patterns are present.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GITIGNORE = ROOT / ".gitignore"


def test_gitignore_has_required_patterns() -> None:
    text = GITIGNORE.read_text(encoding="utf-8")
    required_substrings = [
        ".env",          # .env* pattern or .env
        "node_modules",
        "__pycache__",
        ".venv",
        "!.env.example",
    ]
    missing = [s for s in required_substrings if s not in text]
    assert not missing, f".gitignore missing required patterns: {missing}"
    # Must not accidentally negate all env protection in a broken way: .env* should be ignored.
    assert ".env*" in text or "\n.env\n" in text or ".env.local" in text, (
        ".gitignore must ignore env files (e.g. .env*)"
    )
