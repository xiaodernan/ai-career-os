"""The repository layout in architecture.md §3 names the packages that exist, and only those.

§3 is the map a newcomer reads first, and it had drifted by five entries: `report/`
(dashboard), `activity/` (agent runs + AI usage), `ai/` (the ai-service client and SSE relay),
`ratelimit/`, `health/` and `storage/` all exist on disk without a line in the tree, while
`billing/` -- which the tree still listed for AI usage accounting -- has not existed since that
accounting moved into `activity`. A map that names the wrong places is worse than no map: the
reader goes looking for `billing/` and concludes the cost feature was removed.

This gate walks the two trees that matter (the backend's package list and the ai-service's
`app/` modules) in both directions: every directory on disk must appear in the doc's tree, and
every name the tree writes must exist on disk. The doc is parsed, not pinned, so adding a
package means adding a line -- the gate fails until both sides say the same thing.
"""

import re
from pathlib import Path

TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parent.parent
DOC = ROOT / "docs" / "architecture.md"
JAVA_PKG = ROOT / "backend" / "src" / "main" / "java" / "com" / "careeros"
AI_APP = ROOT / "ai-service" / "app"


def read(path: Path) -> str:
    """Shipped text with LF endings; `git archive` hands out CRLF on this host."""
    return path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")


def layout() -> str:
    text = read(DOC)
    return text[text.index("## 3. Repository layout"):text.index("## 4.", text.index("## 3."))]


def block(start_marker: str, end_marker: str) -> str:
    tree = layout()
    start = tree.index(start_marker)
    return tree[start:tree.index(end_marker, start)]


def backend_block() -> str:
    return block("com/careeros/", "├── ai-service/")


def ai_block() -> str:
    tree = layout()
    start = tree.index("└── app/")
    start = tree.index("\n", start)  # the app/ line itself is the container, not a module
    return tree[start:tree.index("├── frontend/", start)]


def named_in(block_text: str) -> set[str]:
    """Every directory the tree writes in that block: `├── name/` or `└── name/`."""
    return set(re.findall(r"[├└]── (\w+)/", block_text))


def on_disk(root: Path) -> set[str]:
    return {p.name for p in root.iterdir() if p.is_dir() and p.name != "__pycache__"}


def test_the_layout_names_every_backend_package_on_disk():
    disk = on_disk(JAVA_PKG)
    tree = named_in(backend_block())
    assert sorted(disk - tree) == [], (
        f"backend packages the layout does not name: {sorted(disk - tree)} -- a reader of §3 "
        f"cannot find them")
    assert sorted(tree - disk) == [], (
        f"the layout names backend packages that do not exist: {sorted(tree - disk)}")


def test_the_layout_names_every_ai_service_module_on_disk():
    disk = on_disk(AI_APP)
    tree = named_in(ai_block())
    assert sorted(disk - tree) == [], (
        f"ai-service modules the layout does not name: {sorted(disk - tree)}")
    assert sorted(tree - disk) == [], (
        f"the layout names ai-service modules that do not exist: {sorted(tree - disk)}")


def test_the_two_blocks_are_actually_the_ones_being_read():
    """Positive control: both parsers found a real block, not an empty slice of prose."""
    assert len(named_in(backend_block())) >= 13, named_in(backend_block())
    assert "providers" in named_in(ai_block()) and "rag" in named_in(ai_block())
    assert len(named_in(ai_block())) >= 10, named_in(ai_block())
