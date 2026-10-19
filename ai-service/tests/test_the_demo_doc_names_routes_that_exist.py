"""The demo script names routes the product actually serves -- API and pages.

Both halves of the walkthrough are pinned: the journey table's page column against the
Next.js `page.tsx` tree, and the API-equivalents table against the backend controllers.

`docs/DEMO.md` tells a presenter which endpoint backs each step. A path there that no
controller serves sends the demo to a 404 in front of an audience -- the same failure the
internal-surface gate exists to prevent, one layer out. This walks every `/api/v1/...`
literal in the doc and every mapping on a `/api/v1` controller, normalises path parameters
(`{id}` / Spring `**` both read `{}`), and fails if the doc names a path the backend does
not mount.

One direction only: the doc is a *curated* walkthrough, not an exhaustive route list, so a
served route the demo omits is fine. A positive control pins a floor on both populations so
a regex that silently matches nothing cannot pass.
"""

import re
from pathlib import Path

TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parent.parent
JAVA = ROOT / "backend" / "src" / "main" / "java"
DOC = ROOT / "docs" / "DEMO.md"

PREFIX = "/api/v1"
APP = ROOT / "frontend" / "src" / "app"
MIN_SERVED = 20
MIN_NAMED = 8
MIN_PAGES_NAMED = 8
MIN_PAGES_ON_DISK = 15


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")


def norm(path: str) -> str:
    return re.sub(r"\{[^}]*\}|\*\*", "{}", path)


def named_in_doc() -> set[str]:
    """Every `/api/v1/...` the demo script mentions (in a table or in prose)."""
    text = read(DOC)
    return {norm(m) for m in re.findall(r"/api/v1/[A-Za-z0-9_{}/-]+", text)}


def served_by_backend() -> set[str]:
    """Every path a controller mounted under `/api/v1` serves."""
    out = set()
    for path in sorted(JAVA.rglob("*Controller.java")):
        text = read(path)
        base = re.search(r'@RequestMapping\("([^"]+)"\)', text)
        base = base.group(1) if base else ""
        if not base.startswith(PREFIX):
            continue
        for match in re.finditer(
                r'@(?:Get|Post|Put|Patch|Delete)Mapping'
                r'(?:\(\s*(?:value\s*=\s*)?"([^"]*)"\s*[,)])?', text):
            sub = match.group(1) or ""
            out.add(norm((base + sub).replace("//", "/")))
    return out


def test_the_demo_names_no_phantom_route():
    named, served = named_in_doc(), served_by_backend()
    assert len(named) >= MIN_NAMED, f"only {len(named)} paths parsed from the demo -- regex drift?"
    assert len(served) >= MIN_SERVED, f"only {len(served)} routes walked -- controller walk drift?"
    phantom = sorted(named - served)
    assert phantom == [], (
        f"docs/DEMO.md names routes the backend does not serve: {phantom} -- a presenter "
        f"following the script would hit a 404")


def test_the_demo_covers_the_core_loop():
    """A sanity floor: the script must name the load-bearing steps, not a random subset."""
    named = named_in_doc()
    for path in ("/api/v1/auth/register", "/api/v1/jobs", "/api/v1/jobs/{}/match",
                 "/api/v1/growth-report"):
        assert path in named, f"the demo no longer names {path}"


# ---------------- pages the journey walks ----------------

def page_paths_in_doc() -> set[str]:
    """Page paths from the journey table's 'Page' column (not the API column)."""
    out: set[str] = set()
    for line in read(DOC).splitlines():
        if not line.startswith("| "):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2 or not cells[0].isdigit():
            continue  # header / separator / prose rows are not journey steps
        for m in re.findall(r"`(/[A-Za-z0-9_\[\]/-]*)`", cells[1]):
            if not m.startswith("/api"):
                out.add(m)
    return out


def frontend_pages() -> set[str]:
    """Every page route the Next.js app tree mounts (route groups stripped)."""
    out: set[str] = set()
    for page in sorted(APP.rglob("page.tsx")):
        rel = page.relative_to(APP).parent.as_posix()
        parts = [x for x in rel.split("/") if x and not x.startswith("(")]
        out.add("/" + "/".join(parts) if parts else "/")
    return out


def test_the_demo_names_no_phantom_page():
    named, pages = page_paths_in_doc(), frontend_pages()
    assert len(named) >= MIN_PAGES_NAMED, \
        f"only {len(named)} pages parsed from the journey table -- regex drift?"
    assert len(pages) >= MIN_PAGES_ON_DISK, \
        f"only {len(pages)} page routes walked -- app tree drift?"
    phantom = sorted(named - pages)
    assert phantom == [], (
        f"docs/DEMO.md walks pages the frontend does not mount: {phantom} -- the presenter "
        f"would open a blank route")


def test_the_demo_walks_the_core_pages():
    named = page_paths_in_doc()
    for path in ("/resumes", "/jobs", "/growth", "/copilot"):
        assert path in named, f"the demo no longer walks {path}"
