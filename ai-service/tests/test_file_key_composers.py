"""A file key is written by two composers in two notations and validated by one anchored pattern.

`documents.file_key` holds either nothing (the inline-text row ai-service writes itself) or a key
minted by one of exactly two Java statements, each of which concatenates a freshly minted UUID into
a path: `FileIngestService.keyFor` (folder supplied by a caller, extension from a switch that spells
its values WITHOUT a dot and pastes the dot as a separate literal) and `ResumeService.persistUpload`
(folder written inline, extension from a *second* switch whose values each carry their own dot and
with no separator at all). One pattern then decides whether a key can be downloaded at all:
`InternalFileController.FILE_KEY`, anchored both ends, alternating a folder and an extension -- and
nothing in ai-service builds or re-checks a key. The two spellings of one grammar are the hazard: a
composer can drift out of the alternation while every Java test still passes, because a test that
hand-writes `uuid/resumes/uuid.pdf` never asks what the composer concatenates. So each assertion
here re-derives the key from the composer's own parts -- literals, identifier positions, switch arms,
and the folder argument callers actually pass -- and runs it through the pattern parsed out of the
controller. Move a separator, a switch value, a folder literal or either alternation and a case
moves with it.
"""

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MAIN = ROOT / "backend" / "src" / "main"
JAVA = MAIN / "java" / "com" / "careeros"
APP = ROOT / "ai-service" / "app"
RESOURCES = MAIN / "resources"

INGEST_SERVICE = JAVA / "knowledge" / "service" / "FileIngestService.java"
RESUME_SERVICE = JAVA / "resume" / "service" / "ResumeService.java"
CONTROLLER = JAVA / "knowledge" / "web" / "InternalFileController.java"
VALIDATOR = JAVA / "storage" / "FileValidator.java"
MIGRATIONS = RESOURCES / "db" / "migration"
V1 = MIGRATIONS / "V1__init_schema.sql"
PY_PIPELINE = APP / "ingestion" / "pipeline.py"
PY_INGEST = APP / "api" / "ingest.py"

USER_ID = "11111111-1111-4111-8111-111111111111"
BLOB = "33333333-3333-4333-8333-333333333333"

JAVA_MAIN_CLASS = r'fileKey.contains("..") || fileKey.contains("\\")'

JAVA_STRING = re.compile(r'"((?:[^"\\]|\\.)*)"')
ASSIGNMENT = re.compile(r"^\s*(?:(?:final\s+)?\w+\s+)?(\w+)\s*=\s*(.+)$", re.S)
SWITCH_TYPE = re.compile(r"switch\s*\(type\)\s*\{")
SWITCH_ARM = re.compile(r'case\s+([A-Z][A-Z0-9_]*)\s*->\s*"((?:[^"\\]|\\.)*)"\s*;')
ENUM_TYPE = re.compile(r"enum\s+Type\s*\{")
ENUM_CONSTANT = re.compile(r"([A-Z][A-Z0-9_]*)\s*\(")
ALTERNATION = re.compile(r"\(([^()]*)\)")
METHOD_HEAD = re.compile(r"^\s+(?:public|private|protected)\b[^\n;]*\(", re.M)
FOLDER_LOCAL = re.compile(r'String\s+(\w+)\s*=\s*"([^"]*)"')
CHECK_ON_FILE_KEY = re.compile(r"CHECK\s*\([^)]*file_key", re.I)
PATTERN_COMPILE = re.compile(r"Pattern\.compile\(")

# The marks are spelled out because the claims below are about these spellings over a named
# population -- an unlisted spelling would make an absence verdict mean nothing.
FOLDER_MARKS = ('"/resumes/"', '"/knowledge/"', "resumes|knowledge", "String folder")
KEY_SHAPE_MARKS = ("[0-9a-fA-F]", "resumes|knowledge", "\\.(pdf")


def reads(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def unescape_java(text: str) -> str:
    """One Java string literal's source characters, as the running JVM sees them.

    Skipping this is not cosmetic: the validator writes its dot as `\\.` in source, so the raw text
    means "backslash then any character" and refuses every key either composer can build.
    """
    escapes = {"\\": "\\", '"': '"', "n": "\n", "t": "\t", "r": "\r"}
    out, i = [], 0
    while i < len(text):
        char = text[i]
        if char == "\\" and i + 1 < len(text):
            out.append(escapes.get(text[i + 1], "\\" + text[i + 1]))
            i += 2
        else:
            out.append(char)
            i += 1
    return "".join(out)


def matching(text: str, open_at: int, opener: str, closer: str) -> int:
    """The offset of the bracket closing the one at `open_at`."""
    depth = 0
    for index in range(open_at, len(text)):
        if text[index] == opener:
            depth += 1
        elif text[index] == closer:
            depth -= 1
            if depth == 0:
                return index
    raise AssertionError(f"unbalanced {opener!r} at offset {open_at} of {text[:80]!r}...")


def inside(text: str, open_at: int, opener: str, closer: str) -> tuple[str, int]:
    """The contents of the bracket opened at `open_at`, plus the offset just past its closer."""
    end = matching(text, open_at, opener, closer)
    return text[open_at + 1:end], end + 1


def string_literals(text: str) -> list[str]:
    return [unescape_java(lit) for lit in JAVA_STRING.findall(text)]


def declaration(sql: str, column: str) -> tuple[str, bool]:
    """One table column as (declared type, required): the reader a nullable verdict needs.

    It reads the line, not a two-branch regex, because a regex whose optional group never
    participates reports the same shape as one that reads `NOT NULL`.
    """
    lines = [line.strip() for line in sql.splitlines()
             if re.match(rf"^{column}\s", line.strip())]
    assert len(lines) == 1, (
        f"expected exactly one {column} column declaration, found {len(lines)}: {lines}")
    words = lines[0].rstrip(",").split()
    assert len(words) >= 2, f"{lines[0]!r} declares no type for {column}"
    return words[1], "NOT NULL" in lines[0]


def compiled_patterns(path: Path) -> list[str]:
    """Every `Pattern.compile("...")` in a file, reassembled from its own argument."""
    source = reads(path)
    out = []
    for match in PATTERN_COMPILE.finditer(source):
        open_at = match.end() - 1
        argument, _ = inside(source, open_at, "(", ")")
        literals = string_literals(argument)
        if literals:
            out.append("".join(literals))
    return out


def method_spans(path: Path) -> list[tuple[str, str, int, int]]:
    """Each declared method as (name, parameter text, body start offset, body end offset)."""
    source = reads(path)
    out = []
    for header in METHOD_HEAD.finditer(source):
        paren = header.end() - 1
        params, after_params = inside(source, paren, "(", ")")
        brace = source.index("{", after_params)
        _, body_end = inside(source, brace, "{", "}")
        name = header.group(0).rstrip().rstrip("(").split("(")[-1].split()[-1]
        out.append((name, params, brace + 1, body_end))
    return out


def method_of(spans: list[tuple[str, str, int, int]], offset: int) -> str:
    """Which declared method an offset falls inside -- by body range, not by nearest header.

    A repository interface or a static initializer has no readable header, and that is reported as
    an owner no case expects rather than crashing the census that walks the whole tree.
    """
    hits = [name for name, _, start, end in spans if start <= offset < end]
    if len(hits) == 1:
        return hits[0]
    return f"<{len(hits)} methods>"


def validator_pattern() -> str:
    """The one compiled pattern in the download controller."""
    patterns = compiled_patterns(CONTROLLER)
    assert len(patterns) == 1, (
        f"expected exactly one Pattern.compile in {CONTROLLER.name}, found {len(patterns)}: "
        f"{patterns}")
    return patterns[0]


def alternations(pattern: str) -> dict[str, list[str]]:
    """The pattern's alternation groups, keyed by the delimiter that introduces each one.

    A group after `/` is the folder axis and one after a dot is the extension axis -- told apart by
    the preceding character, so the two axes cannot be swapped silently.
    """
    keyed: dict[str, list[str]] = {}
    for match in ALTERNATION.finditer(pattern):
        preceding = pattern[match.start() - 1]
        options = match.group(1).split("|")
        assert all(options), f"empty alternative in group {match.group(0)!r} of {pattern!r}"
        assert preceding not in keyed, (
            f"two alternations introduced by {preceding!r}: {keyed[preceding]!r} and {options!r}")
        keyed[preceding] = options
    assert set(keyed) == {"/", "."}, (
        f"expected the pattern to alternate a folder after a slash and an extension after a dot, "
        f"got groups introduced by {sorted(keyed)} in {pattern!r}")
    return {"folders": keyed["/"], "extensions": keyed["."]}


def key_statements(path: Path) -> list[tuple[str, list[str]]]:
    """Statements in a file that mint a UUID into a string: (method, concatenation parts).

    Each `UUID.randomUUID()` occurrence is turned into its own statement by walking out to the
    brackets and semicolons around it, so a mint that spans lines, or one the header walker cannot
    place, still shows up instead of quietly narrowing the census. `uuid_mints` then pins how many
    mints exist at all.
    """
    source = reads(path)
    spans = method_spans(path)
    out = []
    for match in re.finditer(r"UUID\.randomUUID\(\)", source):
        start = max(source.rfind(";", 0, match.start()), source.rfind("{", 0, match.start()),
                    source.rfind("}", 0, match.start())) + 1
        statement = source[start:source.index(";", match.end())].strip()
        if statement.startswith("return "):
            expression = statement[len("return "):]
        else:
            assign = ASSIGNMENT.match(statement)
            expression = assign.group(2) if assign else statement
        out.append((method_of(spans, match.start()), re.split(r"\s\+\s*", expression.strip())))
    return out


def uuid_mints() -> list[tuple[str, str, list[str]]]:
    """Every `UUID.randomUUID()` in production code, as (file, method, concatenation parts).

    Returned whole so a case can pin the population: a mint that is not joined into a path still
    moves this count, and the census below only means anything with that number in hand.
    """
    out = []
    for path in sorted(JAVA.rglob("*.java")):
        for method, parts in key_statements(path):
            out.append((path.name, method, parts))
    return out


def all_key_composers() -> list[tuple[str, str, list[str]]]:
    """Composers across the production tree: a minted UUID joined into a `/`-bearing string."""
    tagged = [(name, method, parts) for name, method, parts in uuid_mints()
              if any(part.startswith('"/') for part in parts)]
    assert len(tagged) >= 2, (
        f"expected at least the two known key composers under {JAVA}, found {len(tagged)}")
    return tagged


def switch_values(path: Path) -> dict[str, str]:
    """The file's one `switch (type)` as {enum constant: extension literal}."""
    source = reads(path)
    heads = list(SWITCH_TYPE.finditer(source))
    assert len(heads) == 1, (
        f"expected exactly one `switch (type)` in {path.name}, found {len(heads)} -- this gate reads "
        f"the extension authorship off that switch")
    body, _ = inside(source, heads[0].end() - 1, "{", "}")
    arms = SWITCH_ARM.findall(body)
    assert arms, f"the switch in {path.name} has no `case NAME -> literal;` arm"
    return {name: unescape_java(value) for name, value in arms}


def declared_types() -> set[str]:
    """The constants of `FileValidator.Type` -- the only set either switch can be exhaustive over."""
    source = reads(VALIDATOR)
    head = ENUM_TYPE.search(source)
    assert head, f"no `enum Type {{` in {VALIDATOR.name}"
    body, _ = inside(source, source.index("{", head.start()), "{", "}")
    constants = set(ENUM_CONSTANT.findall(body.split(";")[0]))
    assert constants, f"`enum Type` in {VALIDATOR.name} declares no constants"
    return constants


def folder_taking_entries() -> list[tuple[str, int]]:
    """FileIngestService methods that pass a `folder` parameter on to keyFor, with its position."""
    out = []
    for name, params, start, end in method_spans(INGEST_SERVICE):
        body = reads(INGEST_SERVICE)[start:end]
        if "keyFor(" not in body:
            continue
        names = [p.split()[-1] for p in params.split(",") if p.strip()]
        if "folder" in names:
            out.append((name, names.index("folder")))
    assert out, (
        f"no method of {INGEST_SERVICE.name} both declares a `folder` parameter and calls keyFor( -- "
        f"the folder axis is no longer supplied by callers")
    return out


def argument_at(call_text: str, index: int) -> str:
    """The argument at `index` of a call whose text begins at its opening paren."""
    depth, current, args = 0, "", []
    for char in call_text[1:]:
        if char == "(":
            depth += 1
        elif char == ")":
            if depth == 0:
                break
            depth -= 1
        if char == "," and depth == 0:
            args.append(current.strip())
            current = ""
            continue
        current += char
    args.append(current.strip())
    assert index < len(args), f"the call starting {call_text[:60]!r} passes only {len(args)} arguments"
    return args[index]


def caller_supplied_folders() -> dict[str, set[str]]:
    """For each folder-taking entry point, every folder literal an in-tree caller passes it.

    An argument that is neither a literal nor a local assigned a literal is a failure, not a guess:
    the axis is only knowable from the call sites.
    """
    paths = sorted(JAVA.rglob("*.java"))
    locals_by_file = {path.name: dict(FOLDER_LOCAL.findall(reads(path))) for path in paths}
    supplied: dict[str, set[str]] = {}
    for method, index in folder_taking_entries():
        literals: set[str] = set()
        sites = 0
        for path in paths:
            source = reads(path)
            for match in re.finditer(r"\." + re.escape(method) + r"\s*\(", source):
                sites += 1
                argument = argument_at(source[match.end() - 1:], index)
                quoted = JAVA_STRING.fullmatch(argument)
                if quoted:
                    literals.add(unescape_java(quoted.group(1)))
                    continue
                assigned = locals_by_file[path.name]
                assert argument in assigned, (
                    f"{path.name} calls {method}(..) with folder argument {argument!r}, which this "
                    f"gate cannot turn into a literal; make the folder it can reach enumerable here")
                literals.add(assigned[argument])
        supplied[method] = literals
        if not literals:
            assert sites == 0, (
                f"{method}() has {sites} caller(s) and none passes a folder literal this gate can "
                f"read")
    return supplied


def composer_parts(path: Path, method: str) -> list[str]:
    """The concatenation parts of one named composer, straight off its statement."""
    for name, owner, parts in all_key_composers():
        if owner == method and name == path.name:
            return parts
    raise AssertionError(
        f"{method}() of {path.name} no longer mints a UUID into a `/`-joined string -- its key "
        f"grammar is built some other way now")


def inline_folder(path: Path, method: str) -> set[str]:
    """The folder a composer writes into its own concatenation, between the two slashes."""
    out = set()
    for part in composer_parts(path, method):
        if not part.startswith('"'):
            continue
        text = unescape_java(JAVA_STRING.fullmatch(part).group(1))
        if text.count("/") == 2:
            out.add(text.strip("/"))
    assert out, f"{method}() pastes no /folder/ segment into its key"
    return out


def build_key(parts: list[str], folder: str, extension: str) -> str:
    """The key a composer emits, assembled from its own parts with each name resolved."""
    pieces = []
    for part in parts:
        if part.startswith('"'):
            pieces.append(unescape_java(JAVA_STRING.fullmatch(part).group(1)))
        elif part == "userId":
            pieces.append(USER_ID)
        elif part == "folder":
            pieces.append(folder)
        elif part == "UUID.randomUUID()":
            pieces.append(BLOB)
        elif part == "ext":
            pieces.append(extension)
        else:
            raise AssertionError(f"unresolved part {part!r} in the key concatenation")
    return "".join(pieces)


# ---------------------------------------------------------------------- the population, gated


def test_exactly_two_statements_mint_a_file_key_and_three_write_one_to_storage():
    """Every key comes from two concatenations, and no fourth variable reaches the bucket.

    Composers are found by what makes a key a key -- a minted UUID joined into a `/`-bearing string,
    not a method name -- so renaming or moving one cannot hide it from this case.
    """
    composers = all_key_composers()
    assert {(file, method) for file, method, _ in composers} == {
        ("FileIngestService.java", "keyFor"),
        ("ResumeService.java", "persistUpload"),
    }, f"the set of key composers moved: {sorted((f, m) for f, m, _ in composers)}"

    mints = sorted(file for file, _, _ in uuid_mints())
    assert mints == ["FileIngestService.java", "RedisSlidingWindowRateLimiter.java",
                     "ResumeService.java", "TokenService.java"], (
        f"the population of minted UUIDs changed: {mints}. Four mints exist, two of them joined into "
        f"a path; a fifth would have to say whether it composes a key")

    writes, reads_storage = [], []
    for path in sorted(JAVA.rglob("*.java")):
        for match in re.finditer(r"storage\.(put|getBytes)\(\s*(\w+)", reads(path)):
            (writes if match.group(1) == "put" else reads_storage).append((path.name, match.group(2)))
    assert writes == [("FileIngestService.java", "key"), ("FileIngestService.java", "key"),
                      ("ResumeService.java", "key")], (
        f"the bucket is written under another variable, or a different number of times: {writes}")
    assert reads_storage == [("InternalFileController.java", "fileKey")], (
        f"the bucket is read by key somewhere other than the one download route: {reads_storage}")


def test_every_key_a_composer_can_build_is_accepted_by_the_pattern_that_validates_it():
    """The heart of the unit: each composer's own parts, run through the controller's own pattern.

    Three near-miss keys are refused in the same case, so six matches cannot mean "the pattern
    accepts anything".
    """
    pattern = validator_pattern()
    folders_by_composer = {
        "keyFor": set().union(*caller_supplied_folders().values()),
        "persistUpload": inline_folder(RESUME_SERVICE, "persistUpload"),
    }
    built = []
    for path, method in ((INGEST_SERVICE, "keyFor"), (RESUME_SERVICE, "persistUpload")):
        folders = folders_by_composer[method]
        assert folders, f"{method}() can reach no folder at all"
        parts = composer_parts(path, method)
        for folder in sorted(folders):
            for extension in sorted(switch_values(path).values()):
                key = build_key(parts, folder, extension)
                built.append(key)
                assert re.fullmatch(pattern, key), (
                    f"{method}() emits {key!r} for folder {folder!r} with extension {extension!r}, "
                    f"which {CONTROLLER.name}'s pattern refuses -- bytes stored under that name are "
                    f"undownloadable, and ingestion asks for them by exactly this URL")
    assert len(built) == 6, f"expected 3 extensions x 2 folders, built {sorted(built)}"

    refused = {
        "no dot before the extension": f"{USER_ID}/knowledge/{BLOB}pdf",
        "a folder no composer writes": f"{USER_ID}/notes/{BLOB}.pdf",
        "one character short of 36": f"{USER_ID}/knowledge/{BLOB[:-1]}.pdf",
    }
    for label, key in refused.items():
        assert not re.fullmatch(pattern, key), (
            f"the pattern accepts {key!r} ({label}), so the six matches above proved nothing")


def test_the_two_composers_put_the_dot_on_opposite_sides_of_the_concatenation():
    """`keyFor` pastes a separator and its switch values carry none; `persistUpload` is the reverse.

    The asymmetry is why reading one switch is not enough: a helper that collects `case X -> "y"`
    and pastes its own dot would silently ignore the other author.
    """
    a_parts = composer_parts(INGEST_SERVICE, "keyFor")
    b_parts = composer_parts(RESUME_SERVICE, "persistUpload")
    a_literals = [unescape_java(JAVA_STRING.fullmatch(p).group(1)) for p in a_parts
                  if p.startswith('"')]
    b_literals = [unescape_java(JAVA_STRING.fullmatch(p).group(1)) for p in b_parts
                  if p.startswith('"')]

    assert "." in a_literals, (
        f"keyFor no longer pastes a dot separator ({a_literals}) and its switch values carry none, "
        f"so every key it writes lost its extension")
    assert "." not in b_literals, (
        f"persistUpload now separates with a dot ({b_literals}) while its switch values already "
        f"start with one -- that writes `..pdf`")

    a_values = set(switch_values(INGEST_SERVICE).values())
    b_values = set(switch_values(RESUME_SERVICE).values())
    assert all(not value.startswith(".") for value in a_values), (
        f"keyFor's switch began spelling its own dot ({sorted(a_values)}) while the statement also "
        f"pastes one")
    assert all(value.startswith(".") for value in b_values), (
        f"persistUpload's switch lost a dot in {sorted(b_values)} and nothing else adds it")
    assert {v.lstrip(".") for v in a_values} == {v.lstrip(".") for v in b_values}, (
        f"the two composers now cover different file types: {sorted(a_values)} vs {sorted(b_values)}")


def test_both_switches_are_exhaustive_over_the_types_and_neither_hides_a_default():
    """No type may be covered by one author only, and none may be swallowed by a default arm."""
    constants = declared_types()
    a, b = switch_values(INGEST_SERVICE), switch_values(RESUME_SERVICE)
    assert set(a) == constants, (
        f"FileValidator.Type is {sorted(constants)} but keyFor's switch covers {sorted(a)}")
    assert set(b) == constants, (
        f"FileValidator.Type is {sorted(constants)} but persistUpload's switch covers {sorted(b)}")
    for path in (INGEST_SERVICE, RESUME_SERVICE):
        assert not re.search(r"\bdefault\s*->", reads(path)), (
            f"{path.name} gave its extension switch a `default ->` arm, so a new FileValidator.Type "
            f"would route to an extension nobody declared instead of failing to compile")
    pattern = alternations(validator_pattern())["extensions"]
    assert {v.lstrip(".") for v in a.values()} == set(pattern), (
        f"the pattern's extension alternation {pattern} no longer names what the composers write")


def test_the_folder_axis_equals_the_alternation_and_every_folder_is_named_by_a_caller():
    """`/resumes/` is written inline and `/knowledge/` arrives as an argument; the pattern lists both.

    A folder-taking entry point with no caller is reported rather than trusted: the day it gains
    one, that caller's literal has to be enumerable here or the axis stops being knowable.
    """
    from_callers = caller_supplied_folders()
    inline = inline_folder(RESUME_SERVICE, "persistUpload")
    authored = set().union(*from_callers.values()) | inline
    pattern_folders = set(alternations(validator_pattern())["folders"])
    assert authored == pattern_folders, (
        f"the composers can write {sorted(authored)} but {CONTROLLER.name} names "
        f"{sorted(pattern_folders)} -- a key in either difference is stored under a name the "
        f"download route refuses forever, or the pattern admits a name nothing can store")
    unreachable = sorted(method for method, literals in from_callers.items() if not literals)
    assert unreachable == ["uploadAndIngest"], (
        f"the folder-taking entry points with no in-tree caller changed: {unreachable}. If one "
        f"gained a caller, its folder literal is now part of the axis; if one lost the parameter, "
        f"the other half of this case no longer describes the code")
    assert inline == {"resumes"}, (
        f"persistUpload no longer writes /resumes/ inline but {sorted(inline)}")


def test_one_pattern_validates_a_key_and_ai_service_neither_builds_one_nor_re_checks_it():
    """The JVM has a single shape validator; Python pastes the stored key into a URL and stops there.

    Marks and population are spelled out because an unlisted spelling would make the absence half of
    this claim mean nothing.
    """
    java_validators = []
    for path in sorted(JAVA.rglob("*.java")):
        if any(mark in pattern for pattern in compiled_patterns(path) for mark in KEY_SHAPE_MARKS):
            java_validators.append(path.name)
    assert java_validators == ["InternalFileController.java"], (
        f"more than one production class validates the key shape: {java_validators}")

    python_side = sorted(path.name for path in APP.rglob("*.py")
                         if any(mark in reads(path) for mark in KEY_SHAPE_MARKS))
    assert python_side == [], (
        f"ai-service now re-authors the key grammar in {python_side}: the one-validator claim is "
        f"false and the two spellings can disagree")

    naming = sorted(path.name for path in JAVA.rglob("*.java")
                    if any(mark in reads(path) for mark in FOLDER_MARKS))
    assert naming == ["FileIngestService.java", "InternalFileController.java",
                      "KnowledgeService.java", "ResumeService.java"], (
        f"the folder names of a key now appear outside the two composers, the one caller that passes "
        f"one and the one validator: {naming}")


def test_the_pattern_anchors_whole_and_admits_exactly_one_dot():
    """Which is why the route's own `..` and backslash guards cannot be the thing that saves a request.

    The claim is about the pattern's alphabet, so an edit that lets a second dot through turns this
    red and at the same time makes those guards load-bearing.
    """
    pattern = validator_pattern()
    assert pattern.startswith("^") and pattern.endswith("$"), (
        f"the key pattern lost an anchor ({pattern!r}), so a key with something prefixed or appended "
        f"passes and the guards below are all that is left")
    outside_classes = re.sub(r"\[[^]]*\]|\([^)]*\)", "", pattern)
    dots = outside_classes.count(".")
    assert dots == 1, (
        f"the pattern admits {dots} unescaped dot positions ({outside_classes!r}), so `..` can reach "
        f"a match and the route's traversal guard is load-bearing -- this case then has to say which "
        f"key it saves")
    assert "\\" not in outside_classes.replace("\\.", ""), (
        f"the pattern admits a backslash ({outside_classes!r}), so the route's backslash guard is "
        f"now the only thing rejecting one")
    assert JAVA_MAIN_CLASS in reads(CONTROLLER), (
        f"{CONTROLLER.name} no longer guards `..` and a backslash in one condition -- the redundancy "
        f"described above is now a different question")


def test_the_column_holds_a_composed_key_or_nothing_and_no_migration_constraints_its_shape():
    """`file_key` is nullable text with no CHECK anywhere -- the inline-text row depends on that.

    Both scanners are proved against synthetic SQL in the same case, so "no CHECK found" can never
    mean "the scanner read nothing".
    """
    assert declaration(reads(V1), "file_key") == ("text", False), (
        f"documents.file_key is no longer bare nullable text in {V1.name}: "
        f"{declaration(reads(V1), 'file_key')}")
    assert declaration(reads(V1), "media_type") == ("text", True), (
        f"{V1.name}: media_type is the NOT NULL twin this reader tells file_key apart from -- if "
        f"the two now read alike, the reader stopped distinguishing them")
    assert declaration("  file_key  text NOT NULL,", "file_key") == ("text", True), (
        "the reader cannot see a NOT NULL file_key, so its nullable verdict is unfalsified")
    assert declaration(reads(V1), "source_file_key") == ("text", False), (
        f"resumes.source_file_key is the other half of the same key and no longer nullable: "
        f"{declaration(reads(V1), 'source_file_key')}")

    constrained = [path.name for path in sorted(MIGRATIONS.glob("*.sql"))
                   if CHECK_ON_FILE_KEY.search(reads(path))]
    assert constrained == [], (
        f"file_key gained a CHECK in {constrained}; compare it with what the two composers can emit "
        f"instead of asserting that nothing constrains the column")
    assert CHECK_ON_FILE_KEY.search("ALTER TABLE documents ADD CONSTRAINT c CHECK (file_key > '');"), (
        "the CHECK scanner does not fire on a real constraint, so its emptiness is unfalsified")


def test_the_only_reader_that_asks_whether_a_row_has_a_key_is_the_ingestion_branch():
    """A document may exist with no key at all, and exactly one `if` in ai-service knows that.

    One Java lookup, one Python consumer, one NULL author: a reader that assumes a key exists has
    nowhere to hide.
    """
    tree = ast.parse(reads(PY_PIPELINE))
    branch = [node for node in ast.walk(tree)
              if isinstance(node, ast.If) and "file_key" in ast.unparse(node.test)]
    assert len(branch) == 1, (
        f"expected one conditional on file_key in {PY_PIPELINE.name}, found {len(branch)} -- a "
        f"second one would decide the same question in a second place")
    readers = sorted(set(re.findall(r'(\w+)\["file_key"\]', reads(PY_PIPELINE))))
    assert readers == ["doc"], f"a file_key is read off something other than the fetched row: {readers}"

    lookups = sorted({path.name for path in JAVA.rglob("*.java") if "findByFileKey(" in reads(path)})
    assert lookups == ["DocumentRepository.java", "InternalFileController.java"], (
        f"the key-to-row lookup spread: {lookups}")

    calls = [node for node in ast.walk(ast.parse(reads(PY_INGEST)))
             if isinstance(node, ast.Call)
             and isinstance(node.func, ast.Attribute) and node.func.attr == "create_document"]
    assert len(calls) == 1, (
        f"expected the one inline-text document write in {PY_INGEST.name}, found {len(calls)}")
    positional = calls[0].args
    assert len(positional) >= 3 and isinstance(positional[2], ast.Constant) \
        and positional[2].value is None, (
        f"{PY_INGEST.name} no longer writes a NULL file_key, so nothing produces the state the "
        f"ingestion branch exists to distinguish")
    assert re.search(r'if not text:\s*\n\s*raise ParseError\("no file_key', reads(PY_PIPELINE)), (
        "the branch no longer fails loudly when a row has neither a key nor inline text, so a "
        "keyless document silently ingests an empty one")
