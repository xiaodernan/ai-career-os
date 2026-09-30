"""The resume detail response ships `sourceFileKey`; the client reads `fileName` and `fileUrl`.

Two sides of one response that never meet. `ResumeDetail` carries an internal MinIO object key that
no browser, driver or Python module names, while `useResume` fills the two fields the "Original
file" button reads from aliases no record authors -- so the button's guard is never true, and
`next build` cannot see it because the type marks both fields optional.

Both ends of every pin here are parsed from the shipped source. The file never rewrites a
production file, and never imports one.
"""

from __future__ import annotations

import pathlib
import re

TESTS = pathlib.Path(__file__).resolve().parent
AI = TESTS.parent
ROOT = AI.parent

SKIP_PARTS = {"node_modules", "__pycache__", "dist", "build", "target"}

DTO_FILE = "backend/src/main/java/com/careeros/resume/dto/ResumeDtos.java"
SERVICE_FILE = "backend/src/main/java/com/careeros/resume/service/ResumeService.java"
ENTITY_FILE = "backend/src/main/java/com/careeros/resume/entity/Resume.java"
CONTROLLER_FILE = "backend/src/main/java/com/careeros/resume/web/ResumeController.java"
V1_FILE = "backend/src/main/resources/db/migration/V1__init_schema.sql"
ENDPOINTS_FILE = "frontend/src/lib/api/endpoints.ts"
TYPES_FILE = "frontend/src/lib/api/types.ts"
RESOURCES_FILE = "frontend/src/lib/hooks/resources.ts"
PAGE_FILE = "frontend/src/app/(app)/resumes/[id]/page.tsx"

KEY = "sourceFileKey"
SNAKE = "source_file_key"
KEY_RE = re.compile(r"sourceFileKey|source_file_key", re.I)


def read(rel: str) -> str:
    # Both planes this gate runs on differ in line endings (blob LF, working copy CRLF), so every
    # pattern below is written against normalized text.
    return (ROOT / rel).read_text(encoding="utf-8").replace("\r\n", "\n")


def walk(prefix: str, suffixes: tuple[str, ...]) -> list[str]:
    base = ROOT / prefix
    assert base.is_dir(), f"{prefix} is not a directory under {ROOT}"
    out = []
    for path in sorted(base.rglob("*")):
        if not path.is_file() or path.suffix not in suffixes:
            continue
        rel = path.relative_to(ROOT).as_posix()
        if any(part.startswith(".") or part in SKIP_PARTS for part in rel.split("/")):
            continue
        out.append(rel)
    return out


def scan(prefix: str, pattern: re.Pattern, suffixes: tuple[str, ...]) -> list[tuple[str, int, str]]:
    files = walk(prefix, suffixes)
    assert files, f"a scan of {prefix} walked no files, so any verdict about it is about nothing"
    hits = []
    for rel in files:
        for num, line in enumerate(read(rel).split("\n"), 1):
            if pattern.search(line):
                hits.append((rel, num, line.strip()))
    return hits


def balanced(text: str, open_at: int, opener: str = "(", closer: str = ")") -> str:
    depth = 0
    for i in range(open_at, len(text)):
        if text[i] == opener:
            depth += 1
        elif text[i] == closer:
            depth -= 1
            if depth == 0:
                return text[open_at + 1:i]
    raise AssertionError(f"unbalanced {opener}{closer} pair at offset {open_at} of {text[:60]!r}")


def split_top(inner: str, angles: bool) -> list[str]:
    """Split a comma list outside (), [] and {}. `angles` is right for declaration lists only.

    A Java *expression* carries `e -> new X(a, b)`, whose `>` closes a generic that never opened:
    the counter goes negative and every inner comma starts a new argument. Case 1 pins both modes.
    """
    parts, depth, current = [], 0, ""
    for ch in inner:
        if ch in "([{" or (angles and ch == "<"):
            depth += 1
        elif ch in ")]}" or (angles and ch == ">"):
            depth -= 1
        if ch == "," and depth == 0:
            parts.append(current.strip())
            current = ""
        else:
            current += ch
    if current.strip():
        parts.append(current.strip())
    return parts


def components_of(name: str, text: str | None = None) -> list[str]:
    """The declared component *names* of `record NAME(...)` in a Java source, in order."""
    text = read(DTO_FILE) if text is None else text
    match = re.search(rf"\brecord\s+{name}\s*\(", text)
    assert match, f"no `record {name}(` found"
    header = balanced(text, match.end() - 1)
    names = []
    for component in split_top(re.sub(r"\s+", " ", header), angles=True):
        assert component, f"`record {name}` has an empty component slot: {header!r}"
        # annotations (@JsonAlias("x")) precede the type; strip them, then take the trailing word.
        stripped = re.sub(r"@\w+(\([^)]*\))?", " ", component).strip()
        names.append(stripped.split(" ")[-1])
    return names


def declarations(sql: str, column: str) -> list[str]:
    return [line.strip() for line in sql.split("\n") if re.match(rf"^\s*{column}\s+\w", line)]


# --------------------------------------------------------------------------- the gates

def test_the_detail_route_answers_with_one_record_whose_only_fileish_component_is_the_key():
    """GET /resumes/{id} hands back `ResumeDetail`, and exactly one of its components names a file."""
    controller = read(CONTROLLER_FILE)
    assert 'public ResumeDetail detail(' in controller, (
        "the detail handler no longer returns ResumeDetail by name, so the record this gate reads "
        "is not the response body")
    mapping = re.search(r'@RequestMapping\("([^"]*)"\)', controller)
    assert mapping, "the controller has no @RequestMapping to derive the route from"
    tail = mapping.group(1).split("/")[-1]
    endpoints = read(ENDPOINTS_FILE)
    assert re.search(rf"resume:\s*\(id: string\) =>\s*`/{tail}/\$\{{seg\(id\)\}}`", endpoints), (
        f"the client's resume detail path no longer composes to `/{tail}/<id>` from the controller's "
        f"@RequestMapping({mapping.group(1)!r})")

    expression = "f(a, b), e -> g(h, i), 3"
    assert split_top(expression, angles=False) == ["f(a, b)", "e -> g(h, i)", "3"], (
        "the expression splitter no longer keeps a nested call in one argument, so the positions "
        "counted below are guessed")
    assert "e -> g(h, i)" not in split_top(expression, angles=True), (
        "the declaration mode agrees with the expression mode on a lambda, so `angles` does not do "
        "what the helper says and one of the two calls below is right by luck")
    declaration = "UUID id, Map<String, Object> structured"
    assert split_top(declaration, angles=True) == ["UUID id", "Map<String, Object> structured"], (
        "the declaration mode splits a generic's own comma, so a component count is a guess")
    assert len(split_top(declaration, angles=False)) == 3, (
        "both modes now agree on a generic declaration, so the mode chosen for each call below is "
        "not load-bearing and one of them is wrong by luck")
    assert len(components_of("ResumeDetail")) == 14, (
        "the record's own component count changed shape; the Map<String, Object> twins are what the "
        "declaration mode exists for")
    names = components_of("ResumeDetail")
    fileish = [n for n in names if "file" in n.lower()]
    assert fileish == [KEY], (
        f"ResumeDetail names a file in {fileish} of {len(names)} components; the claim pinned below "
        f"is that exactly one of them is authored by the response")
    # the reader has to be able to see a second one, or `fileish == [KEY]` proves nothing
    assert [n for n in components_of("T", 'record T(String title, String fileName) {}')
            if "file" in n.lower()] == ["fileName"], (
            "the component scan cannot name a file field, so its single hit above is unfalsified")

    builds = re.findall(r"new ResumeDetail\(", read(SERVICE_FILE))
    assert len(builds) == 2, (
        f"ResumeDetail is constructed {len(builds)} times in ResumeService, not twice; the arity and "
        f"index pins below are keyed on both projections agreeing")
    text = read(SERVICE_FILE)
    for i, match in enumerate(re.finditer(r"new ResumeDetail\(", text), 1):
        args = split_top(balanced(text, match.end() - 1), angles=False)
        assert len(args) == len(names), (
            f"build #{i} passes {len(args)} arguments to a {len(names)}-component record")
        at = [j for j, arg in enumerate(args) if "getSourceFileKey()" in arg]
        assert at == [names.index(KEY)], (
            f"build #{i} puts the key at argument {at} while the record declares it at "
            f"{names.index(KEY)}; a positional record means the wire name would then describe a "
            f"different value")


def test_the_shipped_key_has_one_writer_and_a_column_that_still_allows_none():
    """Exactly one Java statement writes the value the response ships, and the column may be NULL."""
    writers = scan("backend/src/main", re.compile(r"\bsetSourceFileKey\("), (".java",))
    assert [rel for rel, _, _ in writers if rel != ENTITY_FILE] == [SERVICE_FILE], (
        f"the key is written from {writers} besides the entity's own setter; more than one author "
        f"means the response no longer describes one ingestion trail")
    local = re.search(r"resume\.setSourceFileKey\((\w+)\)", read(SERVICE_FILE))
    assert local and local.group(1) == "key", (
        f"the writer stores {local.group(1) if local else 'nothing'} rather than the composed local, "
        f"so the value reaching the DTO is no longer the one file_key_composers pins")
    readers = scan("backend/src/main", re.compile(r"getSourceFileKey\(\)"), (".java",))
    assert [rel for rel, _, _ in readers if rel != ENTITY_FILE] == [SERVICE_FILE, SERVICE_FILE], (
        f"the detail readers moved: {readers}")

    sql = read(V1_FILE)
    rows = declarations(sql, SNAKE)
    assert len(rows) == 1, (
        f"{SNAKE} is declared {len(rows)} times in V1 ({rows}); the nullability pin below needs one "
        f"authoritative row")
    assert "NOT NULL" not in rows[0], (
        f"the column became required ({rows[0]!r}) while the DTO ships it straight through, so a "
        f"resume with no source file would no longer be storable")

    # the entity is the second author of that verdict, and it has to agree with the migration
    column = re.search(r'@Column\(([^)]*)\)\s*\n\s*private String sourceFileKey;', read(ENTITY_FILE))
    assert column, (
        "the entity no longer declares sourceFileKey under a @Column(...) this scan can read, so "
        "nothing here proves the two agree")
    assert "nullable" not in column.group(1), (
        f"the entity marks the field required ({column.group(1)!r}) while V1 leaves the column "
        f"optional ({rows[0]!r}); the DTO ships whichever of the two wins, and the response would "
        f"promise a value the schema still allows to be missing")
    twin = re.search(r'@Column\(([^)]*)\)\s*\n\s*private String sourceFileKey;',
                     '@Column(name = "x", nullable = false)\n    private String sourceFileKey;')
    assert twin and "nullable" in twin.group(1), (
        "the entity scan cannot see a required declaration, so the agreement above is unfalsified")

    falsifier = declarations("  source_file_key  text NOT NULL,", SNAKE)
    assert len(falsifier) == 1 and "NOT NULL" in falsifier[0], (
        f"declaration() read the required twin as {falsifier}, so the nullable verdict above is "
        f"unfalsified")


def test_the_component_reaches_the_wire_under_its_java_name():
    """No naming strategy and no annotation renames this record's components."""
    strategy = scan("backend/src/main",
                    re.compile(r"PropertyNamingStrateg|SNAKE_CASE|@JsonNaming"), (".java",))
    assert strategy == [], (
        f"a global naming strategy now applies ({strategy}); the response's key may be snake-cased "
        f"and the alias sets compared below would need re-deriving from it")
    config = scan("backend/src/main/resources", re.compile(r"property-naming|naming-strategy", re.I),
                  (".yml", ".yaml", ".properties"))
    assert config == [], f"Jackson is configured in {config}; re-derive the wire name from there"

    header = balanced(read(DTO_FILE),
                      re.search(r"\brecord\s+ResumeDetail\s*\(", read(DTO_FILE)).end() - 1)
    annotated = re.findall(r"@\w+", header)
    assert annotated == [], (
        f"ResumeDetail's components now carry {annotated}; an annotation on a component changes the "
        f"name on the wire without changing the Java name, which is exactly the drift this case "
        f"prevents")
    assert re.findall(r"@\w+", 'record T(@JsonProperty("file_name") String fileName) {}') == \
        ["@JsonProperty"], "the annotation scan cannot see a component annotation, so emptiness is blind"


def test_only_the_schema_and_two_gates_name_the_key_that_ships():
    """Nobody downstream of the response reads it: not the client, not the driver, not the model."""
    sites = sorted({rel for rel, _, _ in scan("", KEY_RE,
                                              (".java", ".py", ".ts", ".tsx", ".sql", ".md",
                                               ".yml", ".yaml", ".mjs", ".json"))})
    assert sites == sorted([DTO_FILE, SERVICE_FILE, ENTITY_FILE, V1_FILE, "docs/architecture.md",
                          "ai-service/tests/test_file_key_composers.py",
                          "ai-service/tests/test_resume_file_fields_ship.py"]), (
        f"the key is now named in {sites}. Anything outside the schema, the two gates and the "
        f"ingestion path is either a reader (the affordance stopped being dead -- then this gate "
        f"must describe what it renders) or a second author")
    frontend = scan("frontend/src", KEY_RE, (".ts", ".tsx"))
    assert frontend == [], (
        f"the browser reads the internal object key at {frontend}; that is the fix, not the bug -- "
        f"rewrite this file around the download flow instead of its absence")
    drivers = scan("e2e", KEY_RE, (".mjs", ".js", ".ts", ".json"))
    assert drivers == [], f"an acceptance driver names the key: {drivers}"


def test_the_names_the_client_reads_are_authored_by_nothing_on_that_response():
    """`fileName` / `fileUrl` are filled from aliases the response's records never declare."""
    hooks = read(RESOURCES_FILE)
    requested: dict[str, set[str]] = {}
    for target, inner in re.findall(r"\b(\w+):\s*str\(([^)]*)\)", hooks):
        names = [n for n in re.findall(r'"([^"]+)"', inner) if n != "body"]
        if names and "resume" in hooks[max(0, hooks.index(f"{target}:") - 400):hooks.index(f"{target}:")].lower():
            requested.setdefault(target, set()).update(names)
    assert {"fileName", "fileUrl"} <= set(requested), (
        f"useResume no longer fills fileName/fileUrl through str(), got {sorted(requested)}; the "
        f"affordance may have been rewired and the claim below is stale")
    for field in ("fileName", "fileUrl"):
        assert field in requested[field], (
            f"the reader for `{field}` no longer asks for the name it exposes, so the pairing the "
            f"gate below pins is not a same-name read")

    detail = components_of("ResumeDetail")
    overlap = sorted((requested["fileName"] | requested["fileUrl"]) & set(detail))
    assert overlap == [], (
        f"the detail record now authors {overlap}; the response could carry a real file name, so "
        f"the button may work and this case must be replaced by the shape that makes it work")

    # one alias does exist in the DTO file -- one level down, where a top-level str() never looks
    records = [m.group(1) for m in re.finditer(r"\brecord\s+(\w+)\s*\(", read(DTO_FILE))]
    assert records, "no records parsed out of ResumeDtos.java, so the nesting claim below is blind"
    holders = sorted(n for n in records if "url" in components_of(n, read(DTO_FILE)))
    assert holders == ["ProjectItem"], (
        f"`url` is authored by {holders}; str(body, ...) reads the detail body's own keys, so a url "
        f"that only exists inside projects[] still cannot fill fileUrl -- unless the client started "
        f"descending, which this pin would then be wrong about")
    header = balanced(read(DTO_FILE), re.search(r"\brecord\s+ResumeDetail\s*\(",
                                                read(DTO_FILE)).end() - 1)
    assert re.search(r"List<ProjectItem>\s+projects", header), (
        "ResumeDetail no longer carries projects as a List<ProjectItem>, so the `url` above is not "
        "the nested one this case excludes")
    assert KEY not in requested["fileName"] | requested["fileUrl"], (
        "the client started asking for the internal key: the leak this file documents is closed, so "
        "pin whatever replaced it")
    # a name may exist deeper in the payload without ever reaching a top-level str() read
    nested = sorted(n for n in ("fileName", "originalName", "file_name", "file_url")
                    if n in read(DTO_FILE))
    assert nested == [], f"an alias the client asks for appears in the DTO file as {nested}"


def test_the_affordance_that_cannot_render_is_gated_on_a_field_the_type_makes_optional():
    """`Original file` renders only under `r.fileUrl`; the type hides that it is never set."""
    page = read(PAGE_FILE)
    sites = scan("frontend/src", re.compile(r"\bfileUrl\b"), (".ts", ".tsx"))
    assert sorted({rel for rel, _, _ in sites}) == sorted([TYPES_FILE, RESOURCES_FILE, PAGE_FILE]), (
        f"fileUrl is named by {sorted({rel for rel, _, _ in sites})} -- one of the three (type, fill, "
        f"render) moved, so the dead-affordance chain below is no longer the whole story")
    guard = re.search(r"\{\s*r\.fileUrl\s*&&\s*\(", page)
    assert guard, "there is no longer an `r.fileUrl &&` guard, so the button's condition changed"
    start = guard.end()
    copy = re.search(r"Original file", page[start:start + 600])
    assert copy, (
        "the guarded block no longer contains the 'Original file' copy, so this case points at a "
        "different affordance")
    assert re.search(r'href=\{r\.fileUrl\}', page[start:start + 600]), (
        "the guarded block contains no anchor built from r.fileUrl")

    types = read(TYPES_FILE)
    interface = balanced(types, types.index("interface Resume"), "{", "}")
    optional = {n: m for n, m in re.findall(r"^\s*(\w+)(\??):", interface, re.M)}
    for field in ("fileName", "fileUrl"):
        assert field in optional, (
            f"the client's Resume type no longer declares {field}, so the fill in useResume has "
            f"nowhere to land and the page read would be a type error")
        assert optional[field] == "?", (
            f"Resume.{field} is required now; tsc would then catch a response that never carries "
            f"it, and this case's claim that only a gate can see the absence is wrong")
    assert KEY not in interface, (
        f"the client type declares {KEY}: the internal object key is now part of the browser's data "
        f"model -- decide whether it is read, and if so replace this file with that flow")
