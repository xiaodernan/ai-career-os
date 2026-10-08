"""Every document the docs name exists, and every document is named by the maps that index them.

Two failure modes, both quiet, and the second one had already happened here.

The first is a reference to a document that is not there. A doc that says "see
`docs/agents.md`" sends a reader to a 404, and the reader cannot tell whether the document
was never written, was renamed, or was deleted on purpose -- so they cannot tell whether
the thing it described still exists either. A map that names the wrong places is worse
than no map: the reader goes looking and concludes the feature was removed.

The second is the mirror image. `PRODUCT.md` -- the document that explains what this
product *is*, in a repository whose whole thesis is that the product is legible -- was
named by nothing. Not the README's repo map, not architecture.md's `docs/` tree entry,
not any companion-doc list, not any cross-reference anywhere in the tree. You had to
already know the filename. Both maps instead listed `agents`, which is at best a nod at
`AGENTS.md` -- the agent instructions, not a design document -- so the one map a newcomer
reads first pointed at the one file in `docs/` that is not about the product.

So references are read as claims and checked both ways. A reference resolves if the file
it names exists at the repo root, beside the referrer, or under the trees that hold
documents; that is deliberately generous, because the failure worth failing on is a name
that exists nowhere, not a path spelled from the wrong base. The repo maps are held to the
stricter standard of naming every document in `docs/`, with `MASTER_PROMPT.md` allowed its
"origin spec" alias since that is what the README calls it and the name is load-bearing.
"""

import re
from pathlib import Path

TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parent.parent
DOCS = ROOT / "docs"
README = ROOT / "README.md"
ARCHITECTURE = DOCS / "architecture.md"
REPORTS = ROOT / "ai-service" / "evals" / "reports"

# The spec names itself; the README calls it "origin spec". Both spellings are the same
# document, and the alias is the one a reader meets first.
ALIASES = {"master_prompt": "origin spec"}


def read(path: Path) -> str:
    """Shipped text with LF endings; `git archive` hands out CRLF on this host."""
    return path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")


def curated_docs() -> list[Path]:
    """The documents a reader is meant to navigate, and nothing generated."""
    out = [README] + sorted(DOCS.glob("*.md"))
    out += [ROOT / "e2e" / "README.md", ROOT / "frontend" / "README.md"]
    return [path for path in out if path.exists()]


def document_files() -> list[Path]:
    """Every file a reference is allowed to name."""
    out = list(curated_docs())
    if REPORTS.is_dir():
        out += sorted(REPORTS.glob("*.md"))
    return out


def known_documents() -> set[str]:
    """Every spelling a reference may use for a document that exists."""
    out: set[str] = set()
    for path in document_files():
        out.add(path.name)
        out.add(path.relative_to(ROOT).as_posix())
        if path.parent != ROOT:
            out.add(path.relative_to(path.parent).as_posix())
    return out


def without_fences(text: str) -> str:
    """Prose only: a fenced block is an instruction or a sample, not a reference."""
    return re.sub(r"```.*?```", "", text, flags=re.S)


def references(path: Path) -> set[str]:
    """Every `.md` file the document names, outside its fenced blocks."""
    return set(re.findall(r"[\w./-]+\.md", without_fences(read(path))))


def repo_map_docs_lines() -> list[str]:
    """The comma-separated document list from each of the two repo maps, folded."""
    out = []
    for path, pattern in (
        (README, r"^docs/\s{2,}(\S.*)$"),
        (ARCHITECTURE, r"^\s*[\u251c\u2514]── docs/\s+#\s*(\S.*)$"),
    ):
        lines = read(path).split("\n")
        for index, line in enumerate(lines):
            found = re.match(pattern, line)
            if not found:
                continue
            folded = [found.group(1).strip()]
            for follow in lines[index + 1 :]:
                if not follow.strip() or not follow[:1].isspace():
                    break
                folded.append(follow.strip())
            out.append(" ".join(folded))
            break
        else:
            raise AssertionError(
                f"{path.name} no longer has a docs/ line in its repo map"
            )
    return out


def entries(line: str) -> set[tuple[str, ...]]:
    """A repo-map line as word tuples, so `product plan` and `product-plan` agree."""
    out = set()
    for entry in line.split(","):
        words = tuple(w for w in re.split(r"[-_+/\s]+", entry.strip().lower()) if w)
        if words:
            out.add(words)
    return out


def spellings(stem: str) -> set[tuple[str, ...]]:
    """Every way a repo map may name the document whose stem is `stem`."""
    plain = tuple(w for w in re.split(r"[-_]+", stem.lower()) if w)
    alias = ALIASES.get("_".join(plain))
    return {plain, tuple(alias.split())} if alias else {plain}


def test_every_document_the_docs_name_is_a_document_that_exists():
    known = known_documents()
    missing = {}
    for path in curated_docs():
        gone = sorted(
            token
            for token in references(path)
            if token not in known and Path(token).name not in known
        )
        if gone:
            missing[path.name] = gone
    assert missing == {}, (
        "these documents name markdown files that exist nowhere in the repository: "
        + "; ".join(f"{name} -> {gone}" for name, gone in sorted(missing.items()))
    )


def test_the_repo_maps_name_every_document_in_docs():
    documents = sorted(path.stem for path in DOCS.glob("*.md"))
    assert len(documents) >= 8, f"only {len(documents)} documents found in docs/"
    for line in repo_map_docs_lines():
        named = entries(line)
        unnamed = [stem for stem in documents if not (spellings(stem) & named)]
        assert unnamed == [], (
            f"a repo map lists {sorted(named)} and never names {unnamed} -- a reader "
            f"navigating from that map cannot reach them"
        )


def test_the_repo_maps_name_nothing_that_is_not_a_document():
    known = {
        spelling
        for stem in (p.stem for p in DOCS.glob("*.md"))
        for spelling in spellings(stem)
    }
    for line in repo_map_docs_lines():
        phantom = sorted(
            " ".join(entry) for entry in entries(line) if entry not in known
        )
        assert phantom == [], (
            f"a repo map names {phantom}, which is no document in docs/ -- the reader "
            f"goes looking for a file that was never written"
        )


def test_the_repo_maps_are_the_two_lines_being_read():
    """Positive control: both parsers found a real list, not an empty slice of prose."""
    for line in repo_map_docs_lines():
        assert len(entries(line)) >= 8, entries(line)
