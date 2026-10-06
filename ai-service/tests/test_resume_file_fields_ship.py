"""The resume detail response ships `sourceFileKey`, and the browser reads it now.

The dead affordance this file used to document went live: `useResume` fills the key the record
authors, the detail page gates "Original file" on it, and the route the key promises bytes from
(`GET /resumes/{id}/file`) is served -- owner-scoped through the document row, named for saving
from that row's title. What remains of the old dead pair is `fileName`/`file_name` asked as
*title* fallbacks by the mappers and a React state name elsewhere -- bloat the mapper census
pins, not this file.

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
    # three reads, all in the service: the list projection, the detail projection, and the
    # download route that turns the key into bytes
    assert [rel for rel, _, _ in readers if rel != ENTITY_FILE] == [SERVICE_FILE] * 3, (
        f"the key's readers moved: {readers}")

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


def test_the_shipped_key_is_read_by_the_three_browser_files_that_render_it():
    """The key is no longer unread: the type declares it, the fill asks it, the page gates on it."""
    sites = sorted({rel for rel, _, _ in scan("", KEY_RE,
                                              (".java", ".py", ".ts", ".tsx", ".sql", ".md",
                                               ".yml", ".yaml", ".mjs", ".json"))})
    assert sites == sorted([DTO_FILE, SERVICE_FILE, ENTITY_FILE, CONTROLLER_FILE, V1_FILE,
                            "docs/API.md", "docs/architecture.md",
                            TYPES_FILE, RESOURCES_FILE, PAGE_FILE,
                            "ai-service/tests/test_file_key_composers.py",
                            "ai-service/tests/test_resources_mapper_records_ship.py",
                            "ai-service/tests/test_resume_file_fields_ship.py"]), (
        f"the key is named in {sites}. The schema, the ingestion trail, the response record, the "
        f"controller's route, the two docs and the three gates are the accounted spellers; a new "
        f"name here is a new author or a new reader, and this census has to say which")

    legs = {rel: [line for f, _n, line in scan("frontend/src", KEY_RE, (".ts", ".tsx"))
                  if f == rel]
            for rel in (TYPES_FILE, RESOURCES_FILE, PAGE_FILE)}
    assert all(legs.values()), (
        f"a leg of the render chain went quiet: { {k: len(v) for k, v in legs.items()} }")
    assert any("sourceFileKey?" in line for line in legs[TYPES_FILE]), (
        "the type no longer declares the key; a resume created by hand then has no honest shape")
    assert any('sourceFileKey: str(body, "sourceFileKey")' in line for line in legs[RESOURCES_FILE]), (
        "useResume stopped filling the key the page gates on")
    assert any("r.sourceFileKey && (" in line for line in legs[PAGE_FILE]), (
        "the affordance's gate moved; re-measure this claim")

    drivers = scan("e2e", KEY_RE, (".mjs", ".js", ".ts", ".json"))
    assert drivers == [], f"an acceptance driver names the key: {drivers}"


def test_the_dead_pair_is_gone_from_the_detail_fill_and_only_title_fallbacks_remain():
    """`fileUrl` / `originalName` are asked nowhere; `fileName` survives only as a title fallback."""
    hooks = read(RESOURCES_FILE)
    assert "fileUrl" not in hooks and "originalName" not in hooks, (
        "the detail fill asks again for a name no producer sends; the dead pair is back")
    assert 'str(body, "sourceFileKey")' in hooks, (
        "useResume stopped reading the key off the detail body")
    remaining = [line.strip() for line in hooks.split("\n")
                 if '"fileName"' in line or '"file_name"' in line]
    assert len(remaining) == 2 and all(line.startswith("title:") for line in remaining), (
        f"fileName survives as {remaining}; a read that is not a title fallback is the dead alias "
        f"coming back through a different field")

    # the only `url` any mapper asks for is the nested one a top-level read never reaches
    records = [m.group(1) for m in re.finditer(r"\brecord\s+(\w+)\s*\(", read(DTO_FILE))]
    assert records, "no records parsed out of ResumeDtos.java, so the nesting claim below is blind"
    holders = sorted(n for n in records if "url" in components_of(n, read(DTO_FILE)))
    assert holders == ["ProjectItem"], (
        f"`url` is authored by {holders}; a top-level url on the detail record would be a second "
        f"way to fill the old fileUrl, and this pin would be wrong about it")
    header = balanced(read(DTO_FILE), re.search(r"\brecord\s+ResumeDetail\s*\(",
                                                read(DTO_FILE)).end() - 1)
    assert re.search(r"List<ProjectItem>\s+projects", header), (
        "ResumeDetail no longer carries projects as a List<ProjectItem>, so the `url` above is "
        "not the nested one this case excludes")


def test_the_live_affordance_gates_on_the_key_and_downloads_from_the_route_the_key_promises():
    """`Original file` renders under `r.sourceFileKey`, saving what GET /resumes/{id}/file answers."""
    page = read(PAGE_FILE)
    guard = re.search(r"\{\s*r\.sourceFileKey\s*&&\s*\(", page)
    assert guard, "the affordance's gate is no longer the key the detail response authors"
    window = page[guard.end():guard.end() + 600]
    assert "Original file" in window, (
        "the guarded block no longer contains the affordance's copy")
    assert "downloadOriginal(r.id" in window, (
        "the affordance is no longer wired to the download call")

    types = read(TYPES_FILE)
    interface = balanced(types, types.index("interface Resume"), "{", "}")
    optional = {n: m for n, m in re.findall(r"^\s*(\w+)(\??):", interface, re.M)}
    assert optional.get("sourceFileKey") == "?", (
        f"Resume.sourceFileKey is {optional.get('sourceFileKey', 'missing')!r}; a resume created by "
        f"hand has no file, so the gate's field has to stay optional")
    for gone in ("fileName", "fileUrl"):
        assert gone not in optional, (
            f"Resume.{gone} is declared again; the type is back to promising a member the "
            f"response does not carry")

    # the bytes behind the gate come from the route the endpoint composes for the controller
    compose = re.search(r"resumeFile:\s*\(id: string\) =>\s*`(/[^`]*)`", read(ENDPOINTS_FILE))
    assert compose, "the client's download endpoint moved"
    controller = read(CONTROLLER_FILE)
    root = re.search(r'@RequestMapping\("([^"]*)"\)', controller)
    leaf = re.search(r'@GetMapping\("(/\{id\}/file)"\)', controller)
    assert root and leaf, "the controller's download route moved"
    client_path = re.sub(r"\$\{seg\(id\)\}", "{id}", compose.group(1))
    assert client_path == root.group(1).removeprefix("/api/v1") + leaf.group(1), (
        f"the client composes {compose.group(1)} while the controller serves "
        f"{root.group(1) + leaf.group(1)}")
