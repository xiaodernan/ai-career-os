"""Markdown doc links in key entry-point docs must resolve to existing files.

Broken links in README.md and docs/DEPLOYMENT.md send operators/readers to dead
ends. This gate extracts relative markdown links to local `.md` files and asserts
each target exists (resolved relative to the linking file).
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS = [
    ROOT / "README.md",
    ROOT / "docs" / "DEPLOYMENT.md",
]

LINK_RE = re.compile(r"\]\(([^)#?]+\.md)\)")


def _resolve(base: Path, target: str) -> Path:
    target = target.strip()
    if target.startswith("/"):
        return ROOT / target.lstrip("/")
    return (base.parent / target).resolve()


def test_key_docs_markdown_links_resolve() -> None:
    missing = []
    for doc in DOCS:
        assert doc.is_file(), f"missing doc: {doc}"
        text = doc.read_text(encoding="utf-8", errors="replace")
        for target in LINK_RE.findall(text):
            # Only local relative/absolute repo links; skip http(s).
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            resolved = _resolve(doc, target)
            if not resolved.exists():
                missing.append(f"{doc.relative_to(ROOT)} -> {target} (resolved {resolved})")
    assert not missing, "broken markdown links:\n" + "\n".join(missing)
