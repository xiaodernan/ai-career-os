"""#191: the resume LIST body, pinned against the mapper that reads it.

`GET /api/v1/resumes` answers `PageDTO<ResumeListItem>`, and `mapResume`
(frontend/src/lib/hooks/resources.ts) is the only mapper that reads that body. #190 covered the
detail record; this file covers the list, which is a different record with five components and a
mapper that asks for twelve names.

Two facts make the list worth its own gate:

* The mapper's alias lists carry seven names no resume list item can answer, and the big reader
  gate (`test_response_field_contract.py`) cannot see any of them: its unbound-mapper ban
  enumerates declarations in `normalize.ts` only, while `mapResume` lives in `resources.ts`.
* One of those dead names is not a typo but a *recovery path* -- the dashboard's score widget ends
  its `??` chain with a read of `score` off the list items, and neither the record nor the mapper
  can ever produce one.
"""

import re
from pathlib import Path

TESTS = Path(__file__).resolve().parent
AI = TESTS.parent
ROOT = AI.parent

BACKEND = ROOT / "backend" / "src" / "main"
JAVA = BACKEND / "java"
RESOURCES = ROOT / "frontend" / "src" / "lib" / "hooks" / "resources.ts"
NORMALIZE = ROOT / "frontend" / "src" / "lib" / "api" / "normalize.ts"
TYPES = ROOT / "frontend" / "src" / "lib" / "api" / "types.ts"
ENDPOINTS = ROOT / "frontend" / "src" / "lib" / "api" / "endpoints.ts"
DASHBOARD = ROOT / "frontend" / "src" / "app" / "(app)" / "dashboard" / "page.tsx"

CONTROLLER = "com/careeros/resume/web/ResumeController.java"
DTO = "com/careeros/resume/dto/ResumeDtos.java"
SERVICE = "com/careeros/resume/service/ResumeService.java"
ENTITY = "com/careeros/resume/entity/Resume.java"

RECORD = "ResumeListItem"

# Measured at this plane; every member is derived from a shipped file by the cases below.
AUTHORED_BY_THE_LIST = {"id", "title", "status", "currentVersionId", "createdAt"}
NAMES_MAP_RESUME_ASKS_FOR = AUTHORED_BY_THE_LIST | {
    "name", "fileName", "file_name", "current_version_id", "created_at",
    "updatedAt", "updated_at",
}

# Shrink-only, one reason each: an unauthored alias the mapper still asks for.
UNAUTHORED_ALIASES = {
    "name": "no resume record carries a `name` component; the entity's column is `title`, so this "
            "alias can only fire on a payload this route never answers",
    "fileName": "no `resume` column and no component; #190 measured the same alias dead on the "
                "detail route, and the list record is smaller still",
    "file_name": "the snake twin of a name nothing authors in either spelling",
    "current_version_id": "the wire name is the Java component `currentVersionId`; no global naming "
                          "strategy renames it, so the snake twin is dead weight",
    "created_at": "same as `current_version_id`: `createdAt` is the name Jackson writes",
    "updatedAt": "`Resume` has the column and a getter, so this alias is one added component from "
                 "alive -- but no resume record ships it today",
    "updated_at": "the snake twin of a name no resume record ships",
}


def read(rel: str) -> str:
    """Read a shipped file with LF endings; `git archive` hands out CRLF on this host."""
    path = Path(rel)
    if not path.is_absolute():
        path = JAVA / rel if (JAVA / rel).exists() else ROOT / rel
    return path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")


def balanced(text: str, open_at: int, opener: str, closer: str) -> int:
    depth = 0
    for i in range(open_at, len(text)):
        if text[i] == opener:
            depth += 1
        elif text[i] == closer:
            depth -= 1
            if depth == 0:
                return i
    raise ValueError(f"no matching {closer!r}")


def declaration_parts(inner: str) -> list[str]:
    """Split a Java declaration list on top-level commas, so generics keep their own commas."""
    parts, buf, depth = [], "", 0
    for ch in inner:
        if ch == "<":
            depth += 1
        elif ch == ">":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append(buf.strip())
            buf = ""
        else:
            buf += ch
    if buf.strip():
        parts.append(buf.strip())
    return parts


def record_components(text: str, name: str) -> list[str]:
    at = text.index(f"record {name}")
    open_at = text.index("(", at)
    inner = text[open_at + 1:balanced(text, open_at, "(", ")")]
    return [part.split()[-1] for part in declaration_parts(inner)]


def function_body(text: str, declaration: str) -> str:
    """A function's body, found by skipping its (possibly multi-line) parameter list.

    Taking the first brace after the name instead would read a destructuring parameter -- the
    dashboard's `ResumeScore` opens with `({ data, resumes }: {...}) {`, whose first brace is the
    parameter object, not the body.
    """
    at = text.index(declaration)
    params_end = balanced(text, text.index("(", at), "(", ")") + 1
    brace = text.index("{", params_end)
    return text[at:balanced(text, brace, "{", "}") + 1]


def mapper_body(text: str, name: str) -> str:
    return function_body(text, "function " + name + "(")


def alias_lists(body: str) -> dict[str, list[str]]:
    """Every `key: fn(raw, "a", "b")` in a mapper body, keyed by the written field.

    The line is not anchored at the closing paren: five of `mapResume`'s six reads continue with a
    `?? fallback`, and an anchored scan found the one line that ends there -- which would have made
    the absence claims below true of an empty set.
    """
    out = {}
    for match in re.finditer(r'^\s*(\w+): (\w+)\(raw((?:,\s*"[^"]*")*)\)', body, re.M):
        keys = re.findall(r'"([^"]*)"', match.group(3))
        if keys:
            out[match.group(1)] = keys
    return out


def test_the_list_route_answers_the_page_envelope_wrapping_the_five_name_item():
    """The route, the endpoint the browser calls and the record's components must be one story."""
    controller = read(CONTROLLER)
    mapping = re.search(r'@RequestMapping\("([^"]+)"\)\s*\n\s*public class ResumeController',
                        controller)
    assert mapping, "the class-level mapping is the prefix of every resume route this gate cites"
    list_route = re.search(r'@GetMapping\s*\n\s*public (PageDTO<ResumeListItem>) list\(', controller)
    assert list_route, "the list handler no longer answers a page of the record this gate pins"
    assert list_route.group(1) == f"PageDTO<{RECORD}>"

    endpoints = read(ENDPOINTS)
    declared = re.search(r'^\s*resumes: "([^"]+)",', endpoints, re.M)
    assert declared.group(1) == mapping.group(1).removeprefix("/api/v1"), \
        "the client's list URL no longer composes to the shipped mapping"

    components = record_components(read(DTO), RECORD)
    assert set(components) == AUTHORED_BY_THE_LIST, \
        f"the list record now answers something else: {sorted(set(components) ^ AUTHORED_BY_THE_LIST)}"

    factory = re.search(r"public static ResumeListItem from\(Resume r\)\s*\{\s*"
                        r"return new ResumeListItem\((.*?)\);", read(DTO), re.S)
    assert factory, "the record no longer builds itself from the entity, so the order below is stale"
    args = [arg.split(".")[-1].rstrip("()") for arg in declaration_parts(factory.group(1))]
    assert args == ["get" + name[:1].upper() + name[1:] for name in components], \
        f"the constructor args and the component order diverge: {args} vs {components}"

    service = read(SERVICE)
    assert f"PageDTO<{RECORD}> list(" in service, \
        "the service no longer builds the page this route returns"
    assert "PageDTO.from(page, ResumeListItem::from)" in service, \
        "the page is built from a different factory, so the five names above are not the answer"


def test_the_mapper_that_reads_the_item_asks_for_seven_names_nothing_answers():
    """Both ends from source: the record's components and the mapper's own alias lists.

    `idStr(raw)` is folded by reading `idStr`'s declaration, because the name it asks for is a
    literal inside that helper -- the same fold the bigger gate documents for its own accessors.
    """
    resources = read(RESOURCES)
    body = mapper_body(resources, "mapResume")
    lists = alias_lists(body)
    assert lists, "the alias scanner found no reads at all, so it proves nothing about absence"

    id_helper = re.search(r'const idStr = .*?pick\(raw, "([^"]*)"', resources, re.S)
    assert id_helper, "`mapResume` writes `id` from a helper whose read this case folds"
    asked = {id_helper.group(1)}
    for keys in lists.values():
        asked |= set(keys)
    assert asked == NAMES_MAP_RESUME_ASKS_FOR, \
        f"the mapper asks for a different name set now: {sorted(asked ^ NAMES_MAP_RESUME_ASKS_FOR)}"

    components = set(record_components(read(DTO), RECORD))
    unauthored = asked - components
    assert unauthored == set(UNAUTHORED_ALIASES), \
        f"off the list: {sorted(unauthored ^ set(UNAUTHORED_ALIASES))}"
    # The scanner is not vacuous: a name the record does answer has to show up as authored.
    assert "title" in asked & components
    assert "title" in lists["title"] and lists["title"][0] == "title", \
        "the title fallback only works because the first alias is the shipped component"
    for alias, why in UNAUTHORED_ALIASES.items():
        assert len(why) > 40, f"{alias} needs a reason a reader can act on, not a label"


def test_a_database_column_name_is_not_a_wire_name_for_the_item():
    """Three of the dead aliases are snake_case twins, so the question is whether anything renames.

    The columns are real -- `current_version_id`, `created_at`, `updated_at` are all
    `@Column(name = ...)` on the entity -- and a JPA column name never reaches JSON. This case
    pins that no annotation and no global strategy renames the list record's components.
    """
    dto = read(DTO)
    at = dto.index(f"record {RECORD}")
    header = dto[at:balanced(dto, dto.index("(", at), "(", ")") + 1]
    assert "@JsonProperty" not in header and "@JsonAlias" not in header, \
        "the list record now renames a component, so the snake aliases above may be alive"

    entity = read(ENTITY)
    columns = set(re.findall(r'@Column\(name = "([^"]+)"', entity))
    assert {"current_version_id", "created_at", "updated_at"} <= columns, \
        "the entity no longer has the columns whose names the mapper's dead twins imitate"
    assert not {"currentVersionId", "createdAt", "updatedAt"} & columns, \
        "a column is now named in camelCase, which would make the twin argument meaningless"

    strategies = scan_for_naming_strategy()
    assert strategies == [], \
        f"a JSON naming strategy appeared ({strategies}) and rewrites every component name"


def scan_for_naming_strategy() -> list[str]:
    """Every shipped property or annotation that could rename JSON keys for this record."""
    found = []
    for path in sorted((BACKEND / "resources").rglob("*.yml")) if (BACKEND / "resources").is_dir() else []:
        text = path.read_text(encoding="utf-8", errors="replace")
        for line in text.split("\n"):
            if "property-naming-strategy" in line:
                found.append(f"{path.name}: {line.strip()}")
    for path in (JAVA / "common").glob("*.java"):
        if "JsonNaming" in path.read_text(encoding="utf-8", errors="replace"):
            found.append(path.name)
    return found


def test_the_dashboard_score_widget_ends_on_a_term_that_can_never_fire():
    """The third `??` term reads `score` off the list items; nothing can answer it, from both ends.

    The two terms before it are alive and this case says so from the producer:
    `normalizeDashboard` writes `score` and `resume.score`. The last one is the recovery path the
    widget advertises -- "fall back to the resumes query" -- and it is dead because the record has
    no `score` component *and* the mapper never writes a `score` key into the object it returns.
    """
    widget = function_body(read(DASHBOARD), "function ResumeScore({")
    chain = re.search(r"const score =\s*\n?(.*?);\n", widget, re.S)
    assert chain, "the widget no longer builds its score from a ?? chain"
    assert chain.group(1).count("??") == 2, \
        f"the score chain changed shape, so the term count below is stale: {chain.group(1)}"
    assert "resumes.data?.items" in chain.group(1), \
        "the list fallback left the chain; delete this case's third-term claim or re-home it"

    normalizer = function_body(read(NORMALIZE), "export function normalizeDashboard")
    assert re.search(r'^\s+score: resumeScore,', normalizer, re.M), \
        "term 1 lost its author"
    assert re.search(r'^\s+resume: rec\(currentResume\)', normalizer, re.M), \
        "term 2 lost its author"

    components = set(record_components(read(DTO), RECORD))
    assert "score" not in components, \
        "the list record now ships a score, which would make the dead term alive -- update the " \
        "widget's claim and this case together"
    assert "score" not in alias_lists(mapper_body(read(RESOURCES), "mapResume")), \
        "mapResume writes a score, so the list fallback is alive again"

    detail = record_components(read(DTO), "ResumeDetail")
    assert "score" in detail, \
        "the score exists only on the detail record; this case's contrast rests on that"


def test_the_dead_aliases_split_into_one_fixable_line_and_two_impossible_names():
    """`updatedAt` is one added component from alive; `fileName` has no column to add.

    The distinction decides what a fix costs, so it is measured rather than asserted: the entity's
    own `@Column` set answers for both, with a twin leg on a name that is authored today.
    """
    entity = read(ENTITY)
    columns = set(re.findall(r'@Column\(name = "([^"]+)"', entity))
    assert "updated_at" in columns, "the entity dropped the column that makes `updatedAt` cheap"
    assert "file_name" not in columns and "fileName" not in columns, \
        "a file-name column exists now, so the mapper's `fileName` alias is no longer impossible"
    assert "title" in columns, "the twin leg needs a name that is authored today"

    getters = set(re.findall(r'public (\w+) get(\w+)\(\)', entity))
    assert any(kind == "OffsetDateTime" and name == "UpdatedAt" for kind, name in getters), \
        "the entity has the column but no getter, so a component could not be added without a fix"

    readers = []
    for path in (ROOT / "frontend" / "src").rglob("*.tsx"):
        text = path.read_text(encoding="utf-8", errors="replace")
        for line in text.split("\n"):
            if "updatedAt" in line and re.search(r"\bresume|\br\.|item\.", line):
                readers.append(f"{path.name}: {line.strip()[:60]}")
    assert readers == [], \
        f"some surface now renders a resume's updatedAt: {readers} -- the dead write became a lie"


def test_the_record_and_the_list_are_named_by_a_pinned_set_of_sites():
    """A census of both ends, so a new consumer has to be registered here before it ships.

    `ResumeListItem` is the record and `useResumes` is the only hook that hands its body to a page.
    Each name's site set is measured by the same walk, which counts this file as a site -- so a
    fourth page, or a Java reader, fails here rather than drifting quietly.
    """
    text_suffixes = {".java", ".py", ".ts", ".tsx", ".sql", ".yml", ".yaml", ".md", ".json"}
    skip_parts = {"node_modules", "__pycache__", "dist", "build", "target"}

    def census(rx: re.Pattern) -> list[str]:
        hits = []
        for path in ROOT.rglob("*"):
            if path.is_dir() or path.suffix not in text_suffixes:
                continue
            rel = path.relative_to(ROOT).as_posix()
            parts = set(rel.split("/"))
            if parts & skip_parts or any(part.startswith(".") for part in parts):
                continue
            if rx.search(path.read_text(encoding="utf-8", errors="replace")):
                hits.append(rel)
        return sorted(hits)

    record_sites = census(re.compile(RECORD))
    assert set(record_sites) == {
        "backend/src/main/java/com/careeros/resume/dto/ResumeDtos.java",
        "backend/src/main/java/com/careeros/resume/service/ResumeService.java",
        "backend/src/main/java/com/careeros/resume/web/ResumeController.java",
        "ai-service/tests/test_resume_list_body_ships.py",
        "ai-service/tests/test_resources_mapper_records_ship.py",
        "ai-service/tests/test_page_window_names_and_their_readers_ship.py",
    }, f"the list record gained or lost a namer: {record_sites}"

    hook_sites = census(re.compile(r"\buseResumes\b"))
    assert set(hook_sites) == {
        "frontend/src/lib/hooks/resources.ts",
        "frontend/src/app/(app)/dashboard/page.tsx",
        "frontend/src/app/(app)/jobs/page.tsx",
        "frontend/src/app/(app)/resumes/page.tsx",
        "ai-service/tests/test_resume_list_body_ships.py",
        "ai-service/tests/test_page_window_names_and_their_readers_ship.py",
        "ai-service/tests/test_window_sizes_whose_callers_decide_them_ship.py",
    }, f"a new surface now reads the list body (gate its fields too), or one stopped: {hook_sites}"

    mapper_sites = census(re.compile(r"\bmapResume\b"))
    assert set(mapper_sites) == {
        "frontend/src/lib/hooks/resources.ts",
        "ai-service/tests/test_resume_list_body_ships.py",
        "ai-service/tests/test_resources_mapper_records_ship.py",
    }, f"mapResume is now named by a new file: if it reaches the mapper differently, the alias " \
        f"table above needs re-deriving, not this set extended: {mapper_sites}"

    # The name appearing in a file is not the declaration existing: arm A10 renamed
    # `function mapResume` and stayed green above, because two call sites still spell the name.
    declared = census(re.compile(r"function mapResume\(raw: unknown\): Resume \{"))
    assert declared == ["frontend/src/lib/hooks/resources.ts"], \
        f"the mapper this gate reads is no longer declared where it claims to be: {declared}"

