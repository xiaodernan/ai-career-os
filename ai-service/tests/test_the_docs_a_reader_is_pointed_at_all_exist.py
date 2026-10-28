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

`EVALUATION.md` names five run reports by their timestamps, and those names are not documents:
`ai-service/evals/reports/` is in `.gitignore`, so a fresh checkout carries none of them. The
first version of this gate therefore had two verdicts for the same tree -- it passed on a machine
that has run the evals and failed on one that has not, because the set of known documents was
grown from whatever report files happened to be on disk. Measured at one commit, both ways: the
archive plane accused those five names of not existing, and the same plane with the locally generated
reports copied into it accused only a different dangling name. That is the same accident as a stale
local build: the reader of the check learns about the machine, not the repository. A generated
reference is now exempted by two conditions the repository itself states -- the path falls under a
directory rule in `.gitignore`, read in the order git reads it so a later `!` line that re-includes
the directory takes the exemption back, and the name carries the `YYYYMMDD-HHMMSS_` stamp the harness
puts on every report it writes -- so the answer is the same on both planes, and a third case refuses
the exemption from widening into a way to hide a real document.
"""

import re
from functools import lru_cache
from pathlib import Path

TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parent.parent
DOCS = ROOT / "docs"
README = ROOT / "README.md"
ARCHITECTURE = DOCS / "architecture.md"
GITIGNORE = ROOT / ".gitignore"

# The spec names itself; the README calls it "origin spec". Both spellings are the same
# document, and the alias is the one a reader meets first.
ALIASES = {"master_prompt": "origin spec"}

# The stamp `app/eval` puts on the front of every report file it writes. A name under an ignored
# directory without it is not a run artifact, and a run artifact is never a document.
RUN_STAMP = re.compile(r"^\d{8}-\d{6}_")


def read(path: Path) -> str:
    """Shipped text with LF endings; `git archive` hands out CRLF on this host."""
    return path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")


def curated_docs() -> list[Path]:
    """The documents a reader is meant to navigate, and nothing generated."""
    out = [README] + sorted(DOCS.glob("*.md"))
    out += [ROOT / "e2e" / "README.md", ROOT / "frontend" / "README.md"]
    return [path for path in out if path.exists()]


def document_files() -> list[Path]:
    """Every file a reference may name as a document.

    The generated reports deliberately do not join this list, and they are not added by looking at
    the filesystem: they are on disk only on a machine that has run an eval, so a population grown
    from them certifies one plane and accuses another of the same tree. `known_documents()` therefore
    reads the curated set, and `is_run_artifact()` decides the generated class from `.gitignore`.
    """
    return curated_docs()


def segments(reference_or_path: str) -> tuple[str, ...]:
    return tuple(seg for seg in reference_or_path.split("/") if seg)


@lru_cache(maxsize=1)
def ignored_directories() -> list[tuple[str, ...]]:
    """The directory rules the repository keeps out of the repository, as segment tuples.

    Read rather than restated, so a report path stops being a document because the project says it is
    generated, not because this file lists a folder. Only rules that end in `/` count: git lets a bare
    name match a file or a directory, and asking which this one is would mean asking the local
    filesystem -- the question this unit exists to stop asking. Lines are taken in the order
    `.gitignore` writes them and a `!` line un-ignores the rule it repeats, because that is how git
    reads the file and the exemption has to follow it -- the day `ai-service/evals/reports/` is
    committed instead of generated, a reference to one of those reports is a claim about a document
    again.
    """
    state: dict[tuple[str, ...], bool] = {}
    for line in read(GITIGNORE).splitlines():
        line = line.strip()
        if not line or line.startswith("#") or not line.endswith("/"):
            continue
        negated = line.startswith("!")
        rule = segments(line[1:] if negated else line)
        if rule:
            state[rule] = not negated
    return [rule for rule, ignored in state.items() if ignored]


def under_ignored_directory(path_segments: tuple[str, ...]) -> bool:
    """Whether this path lies in a directory `.gitignore` keeps out of the repository.

    A reference and a rule name the same directory from either end of it, so either can be the
    shorter one: `__pycache__/` sits inside a long path, and `evals/reports/<stamp>.md` is how a
    document inside `ai-service/` spells what `.gitignore` writes as `ai-service/evals/reports/`.
    Matching only the first of those would leave the second class unclassified, which is the accident
    this function exists to remove. A name at the repository root has no directory to fall under, and
    the two comparisons below say so by length: no rule is ever shorter than nothing.
    """
    dirs = path_segments[:-1]
    return any(
        rule
        and (
            tuple(dirs[-len(rule) :]) == rule
            if len(rule) <= len(dirs)
            else tuple(rule[-len(dirs) :]) == dirs
        )
        for rule in ignored_directories()
    )


def is_run_artifact(reference: str) -> bool:
    """A generated file the repository declares it does not carry, spelled from any base."""
    parts = segments(reference)
    return (
        bool(parts)
        and under_ignored_directory(parts)
        and (RUN_STAMP.match(parts[-1]) is not None)
    )


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


# Files the *product* hands the reader, written down where the reader sees
# them. The docs name them because the reader finds them on disk -- the
# export page saves `career-os-export.json` and its Markdown half as
# `career-os-export.md`. A gate that sent the reader to look for them in the
# repository would be asking about the wrong file; and unlike the run
# reports, these are named by the product's own writers, so the set is two
# names and stays two.
PRODUCT_OUTPUTS = frozenset({"career-os-export.json", "career-os-export.md"})


def test_every_document_the_docs_name_is_a_document_that_exists():
    known = known_documents()
    missing = {}
    for path in curated_docs():
        gone = sorted(
            token
            for token in references(path)
            if token not in known
            and Path(token).name not in known
            and Path(token).name not in PRODUCT_OUTPUTS
            and not is_run_artifact(token)
        )
        if gone:
            missing[path.name] = gone
    assert missing == {}, (
        "these documents name markdown files that exist nowhere in the repository: "
        + "; ".join(f"{name} -> {gone}" for name, gone in sorted(missing.items()))
        + f"; the generated directories read from {GITIGNORE.name} are "
        f"{[('/'.join(r) + '/') for r in ignored_directories()]}"
    )


def test_a_generated_reference_is_exempt_only_because_the_repository_calls_it_generated():
    """The exemption's own mechanism, so it cannot quietly become a way to hide a document.

    Four things have to be true together. `.gitignore` was read and yielded directory rules -- last
    match wins, so a `!` line that re-includes a directory removes it from that list. At least one
    reference in the docs is classified by them, because an exemption nothing uses is a rule that has
    stopped describing the files it was written for and will exempt the next dangling name just as
    easily. Every classified reference is re-derived from both conditions, not trusted from the
    classifier. And no curated document falls inside one of those directories -- the day someone
    ignores `docs/`, every reference to a real design document stops being checked, and that has to
    cost this gate its green.
    """
    rules = ignored_directories()
    assert rules, (
        f"{GITIGNORE.name} yielded no directory rule, so no reference could be classified as "
        "generated -- the report names would be judged against a checkout that has run the evals, "
        "which is the accident this case exists to remove"
    )
    refs = {token for path in curated_docs() for token in references(path)}
    artifacts = sorted(token for token in refs if is_run_artifact(token))
    assert artifacts, (
        f"no reference in the curated documents is classified as a run artifact, though "
        f"{[('/'.join(r) + '/') for r in rules]} are ignored: either the docs stopped naming reports "
        "by their run stamp, or the stamp and the ignored directory no longer describe the same "
        "files -- and a rule nobody uses will exempt the next dangling name just as easily"
    )
    for token in artifacts:
        assert under_ignored_directory(segments(token)), (
            f"{token} was exempted as generated without falling under an ignored directory"
        )
        assert RUN_STAMP.match(segments(token)[-1]), (
            f"{token} was exempted as generated without the run stamp the harness writes"
        )
    swallowed = sorted(
        path.relative_to(ROOT).as_posix()
        for path in curated_docs()
        if under_ignored_directory(segments(path.relative_to(ROOT).as_posix()))
    )
    assert not swallowed, (
        f"an ignored-directory rule covers {swallowed}: a curated document that lives where "
        f"{GITIGNORE.name} says nothing is carried would stop being a document this gate can check, "
        "and references to it would be exempt forever"
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
        assert len(entries(line)) >= 8, (
            f"a repo map was read as {line!r} and yielded {sorted(entries(line))}, "
            "which is not a document list -- the two map cases would then be judging an empty set "
            "and calling the maps complete and phantom-free at once"
        )
