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

The second exempted class was this gate's own bug. Files the product *hands the reader* -- the
export page's `career-os-export.json`, its Markdown half, a kept letter's download -- are not
documents either, and they were exempted by a list of two names whose comment promised the set
"stays two". The letter download made that sentence false without any doc saying anything wrong:
the roadmap named `cover-letter-senior-frontend-engineer.md`, which is exactly the file the drawer
writes, and the gate called it a dangling document. A list of the names somebody thought of is the
same mistake as the anonymization policy that was a list of fields, so the population is now read
off the browser -- every filename spelled at a `downloadText(...)` argument or a `filename={...}`
prop, followed one hop through the identifier the call hands it to, with each `${...}` hole turned
into a wildcard because a writer produces a family of names and a doc quotes one of its members.
The next download needs no edit here; a download the code stops writing reddens the sentence that
still promises it.
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


@lru_cache(maxsize=None)
def read(path: Path) -> str:
    """Shipped text with LF endings; `git archive` hands out CRLF on this host.

    Cached because the download walk reaches the same browser modules many times over: every
    identifier at every call site asks for the whole source tree, and re-opening those files turned
    a census of six names into a ten-second gate.
    """
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
    # `docs/plans/*.md` are checked-in documents a reader is pointed at (the long-term
    # plan, the expansion backlog and the forward horizon), but `curated_docs()` walks
    # only `docs/*.md`. Leaving them out of the *known* set made every reference to a
    # real, tracked plan read as a dangling file. They join the known set here without
    # joining the walk: what a plan quotes internally is its own prose, not a document
    # the navigation promise has to answer for.
    return curated_docs() + sorted(DOCS.glob("plans/*.md"))


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


# The files the *product* hands the reader, spelled by the code that hands them over.
#
# The docs name these because the reader finds them on disk: the export page saves
# `career-os-export.json` and its Markdown half as `career-os-export.md`, and a kept letter leaves
# as `cover-letter-<the posting's own words>.md`. A gate that sent the reader looking for them in
# the repository would be asking about the wrong file.
#
# They were a list of two names, and the letter download made the list wrong: not because the name
# was missing from it, but because a list is a claim about how many writers there are, and the next
# download would have reddened a document that had said something true. So the population is read
# off the browser instead -- every filename literal at a download site, one hop through the
# identifier the call names (`filename={letterDownloadName(...)}` writes its file inside a
# function, and `downloadText(name, ...)` inside a `const`) -- and a `${...}` hole becomes a
# wildcard, because the writer produces a family of names and the docs quote one of its members.
#
# Two limits keep the exemption from widening into a way to hide a document. Only a *bare* name is
# exempt: `docs/export.md` is a claim about this repository, and a download lands wherever the
# reader's browser lands it. And a string inside a hole is the expression's own text, not a name --
# the download button's fallback is `careeros-${...}`, whose hole mentions `document.md`, and a
# reference to a bare `document.md` is not a file the product ever writes.
FRONTEND = ROOT / "frontend" / "src"

# The two shapes a download is named in: the first argument of the helper that saves the file, and
# the `filename` prop of the button that calls it.
DOWNLOAD_CALL = re.compile(r"\b(?:downloadText|downloadBlob)\(")
DOWNLOAD_PROP = re.compile(r"\bfilename=\{")
# A quoted or templated string that ends in a file the reader is handed. A backtick run may carry
# quotes (the hole in `cover-letter-${stem || "letter"}.md` does); a quoted run may not.
FILENAME_LITERAL = re.compile(
    r"`([^`\n]{1,80}?\.(?:md|json|csv|txt))`"
    r"|(?P<q>[\"'])(?P<quoted>[^\"'\n]{1,80}?\.(?:md|json|csv|txt))(?P=q)")
IDENTIFIER = re.compile(r"\b([A-Za-z_]\w*)\b")
# `name` -> the function that names it -> the literal it returns. Two hops is the deepest the
# writers go; a third would be a scan chasing itself through the module.
MAX_HOPS = 2


@lru_cache(maxsize=1)
def frontend_sources() -> list[Path]:
    """The browser's own code, tests aside: they name sample files no reader is handed."""
    out = [path for path in sorted(FRONTEND.rglob("*"))
           if path.suffix in (".ts", ".tsx") and ".test." not in path.name]
    assert out, f"no browser source under {FRONTEND.relative_to(ROOT)} -- the walk would judge no name"
    return out


def closes_at(text: str, start: int, opening: str) -> int:
    """The index of the pair that closes the one at `start`, or -1."""
    closing = {"(": ")", "{": "}"}[opening]
    depth = 0
    for index in range(start, len(text)):
        if text[index] == opening:
            depth += 1
        elif text[index] == closing:
            depth -= 1
            if depth == 0:
                return index
    return -1


def region_at(text: str, start: int, opening: str, label: str) -> str:
    end = closes_at(text, start, opening)
    assert end >= 0, f"unclosed {label} at {text[start:start + 40]!r}"
    return text[start + 1:end]


def first_argument(region: str) -> str:
    """The download helper's name argument: up to the first comma at bracket depth zero."""
    depth = 0
    for index, char in enumerate(region):
        if char in "([{":
            depth += 1
        elif char in ")]}":
            depth -= 1
        elif char == "," and depth == 0:
            return region[:index]
    return region


def hole_spans(text: str) -> list[tuple[int, int]]:
    """The `${...}` ranges of a template: inside one is an expression, not a name."""
    spans, index = [], 0
    while True:
        start = text.find("${", index)
        if start < 0:
            return spans
        end = closes_at(text, start + 1, "{")
        assert end >= 0, f"unclosed hole at {text[start:start + 40]!r}"
        spans.append((start, end + 1))
        index = end + 1


def blank(text: str, spans) -> str:
    chars = list(text)
    for start, end in spans:
        chars[start:end] = [" "] * (end - start)
    return "".join(chars)


def written_names(region: str) -> list[str]:
    """The filenames of a region, minus any string that only sits inside another template's hole."""
    holes = hole_spans(region)
    return [match.group(1) if match.group(1) is not None else match.group("quoted")
            for match in FILENAME_LITERAL.finditer(region)
            if not any(start <= match.start() < end for start, end in holes)]


def expressions(region: str) -> str:
    """A region with its names and holes removed: what is left is the code that decides the name."""
    stripped = blank(region, hole_spans(region))
    return blank(stripped, [(match.start(), match.end())
                            for match in FILENAME_LITERAL.finditer(stripped)])


def declaration_body(name: str, path: Path) -> str | None:
    """The text a bare identifier's value is written in -- a function's body or a `const`'s."""
    pattern = r"(?P<kind>function|const|let)\s+" + re.escape(name) + r"\s*(?P<tail>[=(])?"
    for candidate in [path] + [p for p in frontend_sources() if p != path]:
        text = read(candidate)
        match = re.search(pattern, text)
        if not match:
            continue
        if match.group("kind") == "function":
            params = closes_at(text, match.start("tail"), "(")
            brace = text.find("{", params) if params >= 0 else -1
            return region_at(text, brace, "{", name) if brace >= 0 else None
        start = match.end()
        while start < len(text) and text[start] in " \t":
            start += 1
        stops = [len(text), text.find(";", start), text.find("\n", start)]
        return text[start:min(stop for stop in stops if stop >= 0)]
    return None


@lru_cache(maxsize=1)
def product_output_writers() -> frozenset[str]:
    """Every filename the browser's own code spells, template holes and all."""
    out, pending, seen = set(), [], set()
    for path in frontend_sources():
        text = read(path)
        for match in DOWNLOAD_CALL.finditer(text):
            region = first_argument(region_at(text, match.end() - 1, "(", "download"))
            pending.append((path, region, 0))
        for match in DOWNLOAD_PROP.finditer(text):
            pending.append((path, region_at(text, match.end() - 1, "{", "filename"), 0))
    while pending:
        path, region, hops = pending.pop()
        out.update(written_names(region))
        if hops >= MAX_HOPS:
            continue
        for name in set(IDENTIFIER.findall(expressions(region))):
            if (path, name, hops) in seen:
                continue
            seen.add((path, name, hops))
            body = declaration_body(name, path)
            if body is not None:
                pending.append((path, body, hops + 1))
    return frozenset(out)


def output_pattern(written: str) -> re.Pattern:
    """A writer's template as the names it produces: each `${...}` hole is one path segment."""
    parts, index = [], 0
    while True:
        hole = written.find("${", index)
        if hole < 0:
            parts.append(re.escape(written[index:]))
            return re.compile("".join(parts))
        parts.append(re.escape(written[index:hole]))
        parts.append("[^/]*")
        end = closes_at(written, hole + 1, "{")
        assert end >= 0, f"unclosed hole in {written!r}"
        index = end + 1


def is_product_output(reference: str) -> bool:
    """Whether the browser itself writes a file by this name -- a bare name, never a path."""
    parts = segments(reference)
    if len(parts) != 1:
        return False
    return any(output_pattern(written).fullmatch(parts[0])
               for written in product_output_writers())


def test_every_document_the_docs_name_is_a_document_that_exists():
    known = known_documents()
    missing = {}
    for path in curated_docs():
        gone = sorted(
            token
            for token in references(path)
            if token not in known
            and Path(token).name not in known
            and not is_product_output(token)
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


def test_the_product_writes_the_names_it_is_exempt_for_and_no_document_is_exempt_with_them():
    """The download exemption's own mechanism, read the same way as the run artifact's.

    Three things have to hold. The walk found names at all, and found one of each shape it claims:
    a name spelled straight into a `downloadText` call, and a name that only arrives through the hop
    into the function the button hands the call -- the letter's `cover-letter-${stem}.md`, written
    one file away from the screen that offers it, is the case the old two-name list could not have
    reached and the reason the list was wrong. At least one reference in the docs is classified by
    the population, because an exemption nothing uses has stopped describing the files it was
    written for. And the two limits bite: a path-spelled name is a claim about this repository, and
    a name inside someone's `${...}` hole is an expression, not a file -- so `docs/API.md` and a bare
    `document.md` stay graded, and the design document that happens to share a stem with a download
    cannot be hidden by one.
    """
    writers = product_output_writers()
    assert writers, f"no filename is written by the browser's code under {FRONTEND.name}/"
    assert {"career-os-export.json", "career-os-export.md"} <= writers, (
        f"the export page's own download names are not in {sorted(writers)}: the walk stopped "
        "finding the call site that hands the reader the bundle")
    assert any("${" in written and written.startswith("cover-letter-") for written in writers), (
        f"{sorted(writers)} carries no templated letter name, so the hop into the function the "
        "button names -- `filename={letterDownloadName(...)}` -- stopped running, and the roadmap's "
        "example letter would be judged a document nobody committed")

    refs = {token for path in curated_docs() for token in references(path)}
    exempted = sorted(token for token in refs if is_product_output(token))
    assert exempted, (
        "no reference in the curated documents is a file the product writes, though the browser "
        f"names {sorted(writers)}: either the docs stopped describing downloads, or the walk no "
        "longer describes the code that makes them -- and a rule nobody uses exempts the next "
        "dangling name just as easily"
    )
    for token in exempted:
        assert len(segments(token)) == 1, (
            f"{token} was exempted as a download while naming a directory: a path is a claim about "
            "this repository, and the reader's browser never lands a download in one"
        )

    assert not is_product_output("docs/API.md"), (
        "a path-spelled design document was exempted by a download name that shares its stem"
    )
    assert not is_product_output("document.md"), (
        "`careeros-${isMarkdown ? \"document.md\" : \"document.txt\"}` is a hole's expression, not a "
        "file the product hands over: the reader's letter never arrives as `document.md`"
    )
    assert not is_product_output("career-os-invented.md"), (
        "a name no writer spells was exempted: the population is the writers, not a prefix"
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
