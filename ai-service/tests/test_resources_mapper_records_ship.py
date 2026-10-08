"""#192: every named mapper in `resources.ts`, bound to the record that answers it.

#191 found that `mapResume` asks for twelve names while `ResumeListItem` answers five, and that the
big reader gate could not see it: `test_response_field_contract.py`'s unbound-mapper ban enumerates
declarations in `normalize.ts` only (its own docstring says "every mapper in normalize.ts"), while
`resources.ts` holds seven more named mappers. The seed for this unit claimed fifteen; the measured
number was seven, and this file said which seven.

At this plane now: eight named mappers -- `mapCompanySource` joined when the company page's detail
screen needed the sources jsonb row-mapped -- and fifty reader calls carrying 109 names. The big
change is mapCompany itself: its eleven calls used to ask thirty-three names of which eleven could
never fire, because the backend stored `culture`, `interviewProcess` and `sources` and answered
none of them. CompanyItem carries all three now and the alias lists are gone -- every name mapCompany
asks is a component of its record, first-spelled -- so its row classifies to nothing and the dead
census dropped from 80 asked names to 56. The resume detail page reads `sourceFileKey` now and the
download route behind it is served -- #155's "Original file" affordance is live, and what is left
of the file-name family is `fileName`/`file_name` asked as title aliases by `mapResume` (harmless
fallbacks, pinned as bloat) and a React state name in source-actions.tsx, which is why those two
share a tier. This file still pins which is which, per name, with the record that answers the route
as the second end.
"""

import re
from pathlib import Path

TESTS = Path(__file__).resolve().parent
AI = TESTS.parent
ROOT = AI.parent

JAVA = ROOT / "backend" / "src" / "main" / "java"
FRONT = ROOT / "frontend" / "src"
RESOURCES = FRONT / "lib" / "hooks" / "resources.ts"
NORMALIZE = FRONT / "lib" / "api" / "normalize.ts"
ENDPOINTS = FRONT / "lib" / "api" / "endpoints.ts"
TYPES = FRONT / "lib" / "api" / "types.ts"
BIG_GATE = TESTS / "test_response_field_contract.py"

RESUME_VERSIONS_TEST = FRONT / "lib" / "hooks" / "resume-versions.test.ts"
VERSIONS_PAGE = FRONT / "app" / "(app)" / "resumes" / "[id]" / "page.tsx"
COMPANIES_PAGE = FRONT / "app" / "(app)" / "companies" / "page.tsx"
KNOWLEDGE_PAGE = FRONT / "app" / "(app)" / "knowledge" / "page.tsx"
INTERVIEWS_PAGE = FRONT / "app" / "(app)" / "interviews" / "page.tsx"

CONTROLLERS = {
    "ResumeController.java": "com/careeros/resume/web/ResumeController.java",
    "ResumeVersionController.java": "com/careeros/resume/web/ResumeVersionController.java",
    "CompanyController.java": "com/careeros/job/web/CompanyController.java",
    "KnowledgeController.java": "com/careeros/knowledge/web/KnowledgeController.java",
    "InterviewController.java": "com/careeros/interview/web/InterviewController.java",
}
RECORD_FILES = {
    "ResumeListItem": "com/careeros/resume/dto/ResumeDtos.java",
    "ResumeDetail": "com/careeros/resume/dto/ResumeDtos.java",
    "ResumeVersionItem": "com/careeros/resume/dto/ResumeDtos.java",
    "CompanyItem": "com/careeros/job/dto/JobDtos.java",
    "CompanyDetail": "com/careeros/job/dto/JobDtos.java",
    "CompanyRequest": "com/careeros/job/dto/JobDtos.java",
    "SourceItem": "com/careeros/knowledge/dto/KnowledgeDtos.java",
    "SessionItem": "com/careeros/interview/dto/InterviewDtos.java",
    "SessionDetail": "com/careeros/interview/dto/InterviewDtos.java",
    "TurnItem": "com/careeros/interview/dto/InterviewDtos.java",
}

# The population this file owns. `None` means the receiver is an element of a bare JSON array, so no
# record sits behind the *envelope* names the call asks for. `mapCompanySource` joined when the
# company page gained the detail screen: the sources jsonb needed its own row mapper, and the
# mapCompany alias lists went away with it -- its eleven calls now ask eleven authored names, first.
NAMED_MAPPERS = ["mapResume", "mapResumeVersions", "mapCompany", "mapCompanySource", "mapSource",
                 "mapSessionScalars", "mapInterviewSessionItem", "mapInterviewSessionDetail"]
EXPORTED_MAPPERS = ["mapResumeVersions", "mapInterviewSessionItem", "mapInterviewSessionDetail"]

ROWS = {
    ("mapResume", "raw"): "ResumeListItem",
    ("mapResumeVersions", "raw"): None,
    ("mapResumeVersions", "v"): "ResumeVersionItem",
    ("mapCompany", "raw"): "CompanyItem",
    ("mapSource", "raw"): "SourceItem",
    ("mapSessionScalars", "s"): "SessionItem",
    ("mapInterviewSessionItem", "s"): "SessionItem",
    ("mapInterviewSessionDetail", "raw"): "SessionDetail",
    ("mapInterviewSessionDetail", "sess"): "SessionItem",
    ("mapInterviewSessionDetail", "t"): "TurnItem",
}

# Measured at this plane: one entry per reader call, keyed by the name the call asks for FIRST. The
# value is the position of the first name that the row's record actually declares, or None when the
# record declares none of them.
CALLED = {
    ("mapResume", "raw"): {"title": 0, "status": 0, "currentVersionId": 0, "createdAt": 0,
                           "updatedAt": None},
    ("mapResumeVersions", "v"): {"resumeId": 0, "label": 0, "versionNo": None, "isCurrent": None,
                                 "kind": 0, "createdAt": 0, "structured": None, "diff": 0},
    ("mapCompany", "raw"): {"name": 0, "website": 0, "logoUrl": 0, "industry": 0, "size": 0,
                            "overview": 0, "techStack": 0, "culture": 0, "interviewProcess": 0,
                            "sources": 0, "openRoleCount": 0},
    ("mapSource", "raw"): {"kind": 0, "title": 0, "status": 0, "error": 0, "chunkCount": None,
                           "createdAt": 0, "updatedAt": None, "taskId": None, "documentId": 0},
    ("mapSessionScalars", "s"): {"jobId": 0, "positionTitle": 0, "companyName": 0, "mode": 0,
                                 "status": 0, "difficulty": 0, "startedAt": 0, "finishedAt": 0},
    ("mapInterviewSessionItem", "s"): {"questionCount": 0, "overall": 0},
    ("mapInterviewSessionDetail", "raw"): {"session": 0, "turns": 0, "evaluation": 0},
    ("mapInterviewSessionDetail", "sess"): {"questionCount": 0, "evaluation": None},
    ("mapInterviewSessionDetail", "t"): {"role": 0},
}
ENVELOPE_CALL = ("mapResumeVersions", "raw", "versions")
ENVELOPE_NAMES = {"versions", "resumeVersions", "resume_versions"}

# Per row: the scanner's call count and name count, and the names no component of this row's record
# answers. Every one of these numbers is derived from the shipped files by the cases below; they are
# written here so a new alias, a moved call or a new component has to be reconciled, not absorbed.
SCANNER_SHAPE = {
    ("mapResume", "raw"): (5, 11),
    ("mapResumeVersions", "raw"): (1, 3),
    ("mapResumeVersions", "v"): (8, 23),
    ("mapCompany", "raw"): (11, 11),
    ("mapSource", "raw"): (9, 21),
    ("mapSessionScalars", "s"): (8, 22),
    ("mapInterviewSessionItem", "s"): (2, 6),
    ("mapInterviewSessionDetail", "raw"): (3, 7),
    ("mapInterviewSessionDetail", "sess"): (2, 4),
    ("mapInterviewSessionDetail", "t"): (1, 1),
}
UNAUTHORED = {
    ("mapResume", "raw"): {"created_at", "current_version_id", "fileName", "file_name", "name",
                           "updatedAt", "updated_at"},
    ("mapResumeVersions", "raw"): ENVELOPE_NAMES,
    ("mapResumeVersions", "v"): {"created_at", "current", "index", "isCurrent", "is_current",
                                 "name", "number", "origin", "resume_id", "source", "structured",
                                 "structuredResume", "structured_resume", "tailorDiff",
                                 "tailor_diff", "title", "versionNo", "version_no"},
    # Empty since the alias lists went away: every name mapCompany asks is a component of
    # CompanyItem in its own spelling, so there is nothing left to classify on this row.
    ("mapCompany", "raw"): set(),
    ("mapSource", "raw"): {"chunkCount", "chunk_count", "chunks", "created_at", "document_id",
                           "errorMessage", "error_message", "fileName", "file_name", "name",
                           "taskId", "task_id", "type", "updatedAt", "updated_at"},
    ("mapSessionScalars", "s"): {"company_name", "createdAt", "created_at", "depth", "jobTitle",
                                 "job_title", "job_id", "kind", "level", "finished_at", "position",
                                 "position_title", "started_at", "type"},
    ("mapInterviewSessionItem", "s"): {"overallScore", "question_count", "score", "turnCount"},
    ("mapInterviewSessionDetail", "raw"): {"answers", "history", "questions", "report"},
    ("mapInterviewSessionDetail", "sess"): {"evaluation", "question_count", "report"},
    ("mapInterviewSessionDetail", "t"): set(),
}

# The strongest of the three classes: a name no record in the backend declares, in either spelling,
# so no route this app can call answers it. The other two classes are derived by rule in the case.
DECLARED_NOWHERE = {
    ("mapResume", "raw"): {"fileName", "file_name"},
    ("mapResumeVersions", "v"): {"current", "index", "isCurrent", "is_current", "number", "origin",
                                 "structuredResume", "structured_resume", "tailorDiff",
                                 "tailor_diff", "versionNo", "version_no"},
    ("mapCompany", "raw"): set(),
    ("mapSource", "raw"): {"chunkCount", "chunk_count", "chunks", "errorMessage", "error_message",
                           "fileName", "file_name", "type"},
    ("mapSessionScalars", "s"): {"depth", "level", "type"},
    ("mapInterviewSessionItem", "s"): {"overallScore", "turnCount"},
    ("mapInterviewSessionDetail", "raw"): {"answers", "report"},
    ("mapInterviewSessionDetail", "sess"): {"report"},
    ("mapInterviewSessionDetail", "t"): set(),
}

# What each screen reads off a mapper's object, and how far each dead name has spread in the
# frontend. The population is every `*.ts*` file under `frontend/src`; the spellings walked are the
# names the mappers ask for, and a camel name and its snake twin are separate entries because a twin
# can be dead in one direction and read in the other.
VERSION_ROW_READS = {"createdAt", "diff", "id", "isCurrent", "label", "score", "source", "versionNo"}
# `sourceFileKey` replaced the two dead reads when the original-file download went live (#155).
RESUME_DETAIL_READS = {"createdAt", "currentVersionId", "id", "score", "sourceFileKey", "status",
                       "structured", "title"}
COMPANY_PAGE_READS = {"id", "industry", "logoUrl", "name", "openRoleCount", "size", "techStack",
                      "website"}
KNOWLEDGE_PAGE_READS = {"error", "id", "kind", "status", "title"}
INTERVIEWS_PAGE_READS = {"companyName", "finishedAt", "id", "jobTitle", "mode", "overall",
                         "questionCount", "startedAt", "status"}
READERS_BY_PAGE = {
    "app/(app)/companies/page.tsx": COMPANY_PAGE_READS,
    "app/(app)/knowledge/page.tsx": KNOWLEDGE_PAGE_READS,
    "app/(app)/interviews/page.tsx": INTERVIEWS_PAGE_READS,
}

# carrier set -> the dead names whose only spelling lives in exactly those files. Measured by this
# file's own census; a name joining or leaving a tier is a fact about the frontend, not about a pin.
# mapCompany's alias names left the census when its asks became authored; `fileName` left the
# screen tier for the wide tier when `source-actions.tsx` began spelling it as a React state name.
DEAD_NAME_TIERS = {
    ("lib/hooks/resources.ts",): {"chunk_count", "error_message", "file_name", "is_current",
                                  "job_title", "position_title", "question_count", "tailorDiff",
                                  "tailor_diff", "turnCount", "version_no"},
    ("lib/api/types.ts", "lib/hooks/resources.ts"): {"chunkCount"},
    ("lib/api/normalize.ts", "lib/hooks/resources.ts"): {"created_at", "current_version_id",
                                                         "overallScore", "structuredResume",
                                                         "structured_resume", "updated_at"},
    ("lib/activity-trace.ts", "lib/hooks/resources.ts"): {"errorMessage", "finished_at",
                                                          "started_at"},
    ("lib/api/endpoints.ts", "lib/hooks/resources.ts"): {"resumeVersions"},
    ("components/common/command-palette.tsx", "lib/api/normalize.ts",
     "lib/hooks/resources.ts"): {"company_name"},
    ("app/(app)/resumes/[id]/page.tsx", "lib/api/types.ts",
     "lib/hooks/resources.ts"): {"isCurrent", "versionNo"},
    ("lib/api/normalize.test.ts", "lib/api/normalize.ts", "lib/hooks/resources.ts"): {"job_id"},
    ("lib/api/normalize.ts", "lib/hooks/resources.ts", "lib/job-filter.ts"): {"resume_versions"},
    ("components/knowledge/source-actions.tsx", "lib/hooks/resources.ts"): {"fileName"},
}
# Beyond three carriers a generic name (`name`, `score`, `title`, `kind`) means something else in the
# file that spells it, so the census stops classifying rather than pretending to.
WIDER_DEAD_NAMES = 28
TYPES_MIRROR_NAMES = {"chunkCount"}
SCREEN_READ_NAMES = {"isCurrent", "versionNo"}


def read(path: Path) -> str:
    """Shipped text with LF endings; `git archive` hands out CRLF on this host."""
    return path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")


def java(rel: str) -> str:
    return read(JAVA / rel)


def balanced(text: str, open_at: int, opener: str, closer: str) -> int:
    depth = 0
    for i in range(open_at, len(text)):
        if text[i] == opener:
            depth += 1
        elif text[i] == closer:
            depth -= 1
            if depth == 0:
                return i
    raise ValueError(f"no matching {closer!r} after offset {open_at}")


def top_level_args(text: str, open_at: int) -> list[str]:
    """Split an argument or component list on commas that are not inside brackets, angles or quotes.

    All three matter here: `Map<String, Object> diff` is one record component, `"tailored-1111"`
    would split on its own comma, and a scanner that tracked only parentheses is what made an
    earlier probe report that `CompanyItem` authored a field named `Map<String`.
    """
    inner = text[open_at + 1:balanced(text, open_at, "(", ")")]
    parts, buf, depth, quote = [], "", 0, None
    previous = ""
    for ch in inner:
        if quote:
            if ch == quote and previous != "\\":
                quote = None
        elif ch in "\"'`":
            quote = ch
        elif ch in "([{<":
            depth += 1
        elif ch in ")]}>":
            depth -= 1
        if ch == "," and depth == 0 and not quote:
            parts.append(buf.strip())
            buf = ""
        else:
            buf += ch
        previous = ch
    if buf.strip():
        parts.append(buf.strip())
    return parts


def record_components(name: str) -> list[str]:
    """A Java record's component names, read from its own declaration."""
    text = java(RECORD_FILES[name])
    at = text.index(f"record {name}")
    return [arg.split()[-1] for arg in top_level_args(text, text.index("(", at))]


def every_record_component() -> dict[str, set[str]]:
    """Every Java record component in the backend, mapped to the records that declare it."""
    found: dict[str, set[str]] = {}
    for path in JAVA.rglob("*.java"):
        text = read(path)
        for match in re.finditer(r"\brecord\s+(\w+)\s*(?:<[^>]*>)?\s*\(", text):
            for arg in top_level_args(text, match.end() - 1):
                if arg.strip():
                    found.setdefault(arg.strip().split()[-1], set()).add(match.group(1))
    return found


def function_body(text: str, declaration: str) -> str:
    """A function's body, found by skipping its (possibly multi-line) parameter list."""
    at = text.index(declaration)
    params_end = balanced(text, text.index("(", at), "(", ")") + 1
    brace = text.index("{", params_end)
    return text[at:balanced(text, brace, "{", "}") + 1]


def mapper_body(name: str) -> str:
    return function_body(read(RESOURCES), f"function {name}(")


def normalize_vararg_readers() -> set[str]:
    """normalize.ts's own readers: a receiver plus string keys, generic or not."""
    return set(re.findall(
        r"^export function (\w+)(?:<[^>]*>)?\(obj: unknown, \.\.\.\w+: string\[\]",
        read(NORMALIZE), re.M))


def resources_reader_vocabulary() -> dict[str, str]:
    """The names resources.ts can call a reader under, resolved through its own import aliases.

    `list as listOf` is why a hand-typed vocabulary is not enough: the file calls `listOf`, and a
    census that looked for `list(` would report that the versions envelope is never read at all.
    """
    exported = normalize_vararg_readers()
    block = re.search(r'import \{([^}]*)\} from "@/lib/api/normalize";',
                      read(RESOURCES), re.S).group(1)
    bound = {}
    for part in (piece.strip() for piece in block.split(",")):
        source, _, local = part.partition(" as ")
        source, local = source.strip(), (local or source).strip()
        if source in exported:
            bound[source] = local
    for local in re.findall(r"^function (\w+)\(raw: unknown, \.\.\.\w+: string\[\]",
                            read(RESOURCES), re.M):
        bound[local] = local
    return bound


def reader_calls(name: str) -> list[tuple[str, str, list[str]]]:
    """(receiver, reader, literal names) for every reader call in a mapper's body, nested included."""
    vocabulary = resources_reader_vocabulary()
    body = mapper_body(name)
    pattern = r"(?<![\w$.])(%s)\s*(?:<[^>]*>)?\(" % "|".join(
        re.escape(local) for local in sorted(vocabulary.values()))
    found = []
    for match in re.finditer(pattern, body):
        args = top_level_args(body, body.index("(", match.end() - 1))
        literals = []
        for arg in args[1:]:
            literal = re.fullmatch(r'"([^"]*)"', arg)
            if literal:
                literals.append(literal.group(1))
        found.append((args[0].strip(), match.group(1), literals))
    return found


def calls_by_receiver(name: str) -> dict[str, list[tuple[str, list[str]]]]:
    grouped: dict[str, list[tuple[str, list[str]]]] = {}
    for receiver, reader, literals in reader_calls(name):
        grouped.setdefault(receiver, []).append((reader, literals))
    return grouped


def snake_of(camel: str) -> str:
    return re.sub(r"(?<=[a-z0-9])([A-Z])", lambda m: "_" + m.group(1).lower(), camel)


def dotted_reads(text: str, variable: str) -> set[str]:
    return {m.group(1) for m in re.finditer(r"(?<![\w$.])" + re.escape(variable) + r"\.(\w+)", text)}


def frontend_files() -> list[str]:
    """Every shipped TS/TSX file under `frontend/src`, as a forward-slash path relative to it."""
    return sorted(str(p.relative_to(FRONT)).replace("\\", "/") for p in FRONT.rglob("*.ts*"))


def carriers_of(name: str) -> set[str]:
    """Which frontend files spell this wire name at all, in this one spelling, in the whole census."""
    return {rel for rel in frontend_files() if re.search(r"\b" + name + r"\b", read(FRONT / rel))}


def test_the_named_mapper_population_matches_the_ledger_and_the_anonymous_half_is_pinned():
    """The census this file owns, plus the half it does not reach.

    `resources.ts` shapes wire bodies in two ways: named `function mapX` declarations, and inline
    arrow mappers passed straight to `normalizePage`. Only the named ones get a row here, so the
    anonymous count is pinned as a number that has to be reconciled rather than left out of the
    census in silence.
    """
    text = read(RESOURCES)
    declared = re.findall(r"^(export )?function (map\w+)\(", text, re.M)
    assert [name for _, name in declared] == NAMED_MAPPERS, \
        f"the mapper population this file binds changed: {[n for _, n in declared]}"
    exported = [name for flag, name in declared if flag]
    assert exported == EXPORTED_MAPPERS, f"export half drifted: {exported}"
    for name in NAMED_MAPPERS:
        sites = sorted(str(p.relative_to(FRONT)).replace("\\", "/")
                       for p in FRONT.rglob("*.ts*")
                       if re.search(r"\bfunction " + name + r"\(", read(p)))
        assert sites == ["lib/hooks/resources.ts"], \
            f"{name} is no longer declared only where this file reads it: {sites}"
    anonymous = re.findall(r"\(\w+\) => \(\{", text)
    assert len(anonymous) == 6, (f"{len(anonymous)} inline arrow mappers in resources.ts; this file "
                                "binds named declarations only, so a new one is an unbound reader "
                                "that has to be added to the census or given a named mapper")


def test_the_reader_vocabulary_is_derived_from_the_helpers_own_signatures():
    """Which functions count as readers is a fact about shipped signatures, not about this file.

    `bool` is exported with the same shape and is not imported: if someone starts calling it, the
    vocabulary has to grow by itself, and the row counts below would go red rather than miss reads.
    """
    exported = normalize_vararg_readers()
    assert exported == {"bool", "list", "num", "pick", "str"}, sorted(exported)
    bound = resources_reader_vocabulary()
    assert bound == {"list": "listOf", "pick": "pick", "str": "str", "num": "num",
                     "strList": "strList"}, bound
    assert "bool" not in bound.values(), "bool is now called here; the census has to see its reads"


def test_the_unbound_mappers_ban_would_find_these_mappers_if_it_read_this_file():
    """The gap #191 exposed, pinned so it cannot be closed by accident in either direction.

    The ban's rule is applied here from its own shipped text: the regex it compiles, and the file it
    feeds it to. The rule finds all eight mappers; the file it reads does not contain them.
    """
    gate = read(BIG_GATE)
    source = re.search(r'^MAPPER_DECL = re\.compile\(r"([^"]*)", re\.M\)$', gate, re.M)
    assert source, "the ban no longer declares its mapper pattern in the shape this file reads"
    pattern = re.compile(source.group(1), re.M)
    assert pattern.pattern == r"^(export )?function (\w+)[<(]", pattern.pattern
    seen = [name for _, name in pattern.findall(read(RESOURCES))]
    # 33 since #218 added `useApplication`, the board's by-id fallback.
    assert len(seen) == 33, f"resources.ts now declares {len(seen)} functions for the ban's rule"
    assert [n for n in seen if n.startswith("map")] == NAMED_MAPPERS, \
        "the ban's own rule no longer recognizes these declarations in file order: " \
        f"{[n for n in seen if n.startswith('map')]}"
    declarations = re.search(r"def _mapper_declarations\(\).*?\n\n", gate, re.S).group(0)
    assert "NORMALIZE.read_text" in declarations, \
        "the ban reads a different file now; this gate's reason for existing has to be re-measured"
    assert "RESOURCES" not in declarations and "resources" not in declarations, \
        "the ban now enumerates resources.ts too -- reconcile the two censuses instead of stacking"
    population = re.search(r"assert len\(population\) == (\d+)", gate)
    assert population and population.group(1) == "34", \
        f"the ban's pinned normalize.ts population moved: {population and population.group(1)}"


def test_the_scanner_finds_the_calls_and_names_each_row_actually_makes():
    """Positive control: every count below is the scan's own, and no row reads empty."""
    for (mapper, receiver), (calls, names) in SCANNER_SHAPE.items():
        found = calls_by_receiver(mapper).get(receiver, [])
        assert found, f"{mapper}/{receiver} scanned no reader calls at all"
        assert len(found) == calls, f"{mapper}/{receiver}: {len(found)} calls, pinned {calls}"
        assert sum(len(lit) for _, lit in found) == names, \
            f"{mapper}/{receiver}: {sum(len(lit) for _, lit in found)} names, pinned {names}"
    assert sum(len(v) for v in CALLED.values()) == 49, "the call table and the scan disagree"
    assert sum(SCANNER_SHAPE[key][0] for key in SCANNER_SHAPE) == 50
    assert sum(SCANNER_SHAPE[key][1] for key in SCANNER_SHAPE) == 109
    # The one call the table above does not key is the envelope's: its receiver has no record, so it
    # is classified by payload shape in its own case instead of by a first authored name here.
    envelope = calls_by_receiver("mapResumeVersions")[ENVELOPE_CALL[1]]
    assert [reader for reader, _ in envelope] == ["listOf"], envelope
    assert set(envelope[0][1]) == ENVELOPE_NAMES, envelope
    assert sum(len(v) for v in CALLED.values()) == \
        sum(SCANNER_SHAPE[key][0] for key in SCANNER_SHAPE) - len(envelope)


def test_every_call_is_classified_against_the_record_behind_its_receiver():
    """The table is derived, not asserted: each row's calls, names and first-authored positions.

    Eight calls have no authored name at all -- `None` below, which is what makes the mapper's
    fallback the entire result -- and since mapCompany's alias lists went away, no call asks its
    record's name third any more.
    """
    for (mapper, receiver), record in ROWS.items():
        found = calls_by_receiver(mapper)[receiver]
        if record is None:
            continue
        authored = record_components(record)
        keyed = {lit[0]: next((index for index, n in enumerate(lit) if n in authored), None)
                 for _, lit in found}
        assert keyed == CALLED[(mapper, receiver)], \
            f"{mapper}/{receiver} no longer calls in the order the record answers: {keyed}"
    first_authored = [v for table in CALLED.values() for v in table.values()]
    assert first_authored.count(0) == 41, first_authored.count(0)
    assert first_authored.count(2) == 0, "a call asks its record's name third; re-measure which"
    assert first_authored.count(None) == 8, \
        f"{first_authored.count(None)} calls can never return a value, pinned 8"


def test_an_unauthored_name_is_a_snake_twin_a_foreign_name_or_a_name_no_record_declares():
    """The partition, and the one class that is a fact about every route rather than about one row."""
    everywhere = every_record_component()
    # The foreign-name lookup is only as good as this census, so its size is pinned from the scan
    # itself rather than left as a floor a narrowing walk could satisfy by reading nothing.
    # 215 rather than 213 since `offerCompensation`/`rejectionReason`: the outcome pair the tracker's
    # ApplicationItem and UpdateApplicationRequest both carry.
    assert len(everywhere) == 215, f"the backend record census read {len(everywhere)} component names"
    assert {"id", "title", "status", "createdAt"} <= set(everywhere), sorted(list(everywhere)[:8])
    scanned_unauthored = scanned_nowhere = 0
    for (mapper, receiver), record in ROWS.items():
        if record is None:
            assert set(UNAUTHORED[(mapper, receiver)]) == ENVELOPE_NAMES
            scanned_unauthored += len(ENVELOPE_NAMES)
            continue
        asked = {n for _, literals in calls_by_receiver(mapper)[receiver] for n in literals}
        authored = set(record_components(record))
        unauthored = asked - authored
        assert unauthored == UNAUTHORED[(mapper, receiver)], \
            f"{mapper}/{receiver} asks new names or the record dropped some: " \
            f"{sorted(unauthored ^ UNAUTHORED[(mapper, receiver)])}"
        twins = {n for n in unauthored if n in {snake_of(a) for a in authored}}
        foreign = {n for n in unauthored - twins
                   if n in everywhere or snake_of(n) in everywhere
                   or any(snake_of(k) == n for k in everywhere)}
        nowhere = unauthored - twins - foreign
        assert nowhere == DECLARED_NOWHERE[(mapper, receiver)], \
            f"{mapper}/{receiver} names nothing declares moved: " \
            f"{sorted(nowhere ^ DECLARED_NOWHERE[(mapper, receiver)])}"
        assert twins | foreign | nowhere == unauthored
        assert not (twins & foreign) and not (twins & nowhere)
        scanned_unauthored += len(unauthored)
        scanned_nowhere += len(nowhere)
    # Both ledger numbers come out of the scan above, so a row that stops reading names narrows the
    # total and gets named, instead of a table quietly agreeing with itself.
    assert scanned_unauthored == 68, scanned_unauthored
    assert scanned_nowhere == 30, scanned_nowhere


def test_no_naming_strategy_and_no_annotation_renames_an_answer_record():
    """Why the snake twins of an authored component are dead weight rather than a second spelling.

    Without this, half the unauthored names would be arguable: a Jackson naming strategy, or a
    `@JsonProperty` on a component, would make the twin answer real.
    """
    backend = ROOT / "backend"
    sources = sorted(p for ext in ("*.java", "*.yml", "*.yaml", "*.properties", "*.xml")
                     for p in backend.rglob(ext))
    assert len(sources) > 100, f"the backend source census read {len(sources)} files"
    for needle in ("property-naming-strategy", "JsonNaming", "PropertyNamingStrateg"):
        found = sorted(str(p.relative_to(backend)).replace("\\", "/")
                       for p in sources if needle in read(p))
        assert found == [], f"{needle} is configured in {found}; the snake twins are live now"
    for record in {rec for rec in ROWS.values() if rec}:
        text = java(RECORD_FILES[record])
        header = text[text.index(f"record {record}"):
                     balanced(text, text.index("(", text.index(f"record {record}")), "(", ")") + 1]
        assert "@JsonProperty" not in header and "@JsonAlias" not in header, \
            f"{record} now renames a component; the twin rule has to be re-measured"


def test_both_version_routes_answer_a_bare_list_so_the_three_envelope_names_never_fire():
    """`listOf(raw, "versions", ...)` asks for keys on a payload that has no keys.

    The names are not merely unauthored: `list()` returns the array before consulting them, and the
    frontend's own test already asserts the envelope reading yields no rows.
    """
    controller = java(CONTROLLERS["ResumeVersionController.java"])
    mapping = re.search(r'@RequestMapping\("([^"]+)"\)', controller).group(1)
    assert 'resumeVersions: "/resume-versions"' in read(ENDPOINTS), "the client's path moved"
    assert mapping == "/api/v1" + re.search(r'resumeVersions: "([^"]+)"', read(ENDPOINTS)).group(1)
    assert "java.util.List<ResumeVersionItem> list(" in controller, \
        "the versions route no longer answers a bare list; the envelope names became reachable"
    assert "ResumeVersionItem get(" in controller, \
        "the single-version route answers something else now; re-read the row it feeds"
    resume = java(CONTROLLERS["ResumeController.java"])
    assert "List<ResumeVersionItem> versions(" in resume, \
        "the second versions route changed shape too"
    normalize = read(NORMALIZE)
    list_body = function_body(normalize, "export function list<T = unknown>(")
    assert "if (Array.isArray(obj)) return obj as T[];" in list_body, \
        "list() no longer returns early on an array, so these names could fire"
    assert normalizePage_call("mapResumeVersions") is None, \
        "mapResumeVersions is now wrapped in a page envelope; re-measure this claim"
    assert "mapResumeVersions(RESUME_DETAIL)" in read(RESUME_VERSIONS_TEST), \
        "the frontend test that pins the empty envelope reading is gone"


def normalizePage_call(mapper: str) -> str | None:
    """The call site where `mapper` is handed to `normalizePage`, if resources.ts has one."""
    match = re.search(r"normalizePage\([^;]*?, " + mapper + r"\)", read(RESOURCES), re.S)
    return match.group(0) if match else None


def test_each_row_sits_behind_a_route_whose_signature_names_that_record():
    """The second end of every row: the controller's own return type, not this file's guess."""
    routes = [
        ("mapResume", "ResumeController.java", "PageDTO<ResumeListItem> list(", "resumes"),
        ("mapResumeVersions", "ResumeVersionController.java",
         "java.util.List<ResumeVersionItem> list(", "resumeVersions"),
        ("mapCompany", "CompanyController.java", "PageDTO<CompanyItem> list(", "companies"),
        ("mapSource", "KnowledgeController.java", "PageDTO<SourceItem> sources(", "knowledge"),
        ("mapSessionScalars", "InterviewController.java", "PageDTO<SessionItem> list(",
         "interviews"),
        ("mapInterviewSessionItem", "InterviewController.java", "PageDTO<SessionItem> list(",
         None),
        ("mapInterviewSessionDetail", "InterviewController.java",
         "SessionDetail detail(", None),
    ]
    for mapper, controller, signature, endpoint_key in routes:
        text = java(CONTROLLERS[controller])
        assert signature in text, f"{controller} no longer ships {signature!r} for {mapper}"
        record = re.search(r"(?:PageDTO<|List<|java\.util\.List<)?(\w+)>? \w+\(", signature).group(1)
        assert record in RECORD_FILES, f"{record} is not a record this file can read"
        rows = [rec for (named, _), rec in ROWS.items() if named == mapper]
        assert record in rows, f"{mapper} is bound to {rows}, not to {record}"
        if endpoint_key:
            path = "/api/v1" + re.search(rf'{endpoint_key}: "([^"]+)"', read(ENDPOINTS)).group(1)
            mapping = re.search(r'@RequestMapping\("([^"]+)"\)', text).group(1)
            assert path.startswith(mapping), f"{endpoint_key}: the client calls {path}, {controller} " \
                f"is mounted at {mapping}"
            tail = path[len(mapping):]
            if tail:
                # A client path longer than the mount is a method-level route, and the controller
                # has to actually carry that tail -- `knowledge` is the one row here whose sources()
                # method adds "/sources" below the class mapping.
                assert f'@GetMapping("{tail}")' in text, \
                    f"{controller} mounts {mapping} but answers nothing at {tail}"
    # The company page's detail route stopped answering the item record bare: it wraps the item and
    # the open-role list in `CompanyDetail`, and `mapCompany` still binds the item that `.company`
    # carries -- so the wrapper is pinned by its own components instead of a route row above.
    company_controller = java(CONTROLLERS["CompanyController.java"])
    assert "CompanyDetail get(" in company_controller, \
        "the company page's route answers something else now"
    assert set(record_components("CompanyDetail")) == {"company", "openRoles"}
    assert 'interviews: "/interview/sessions"' in read(ENDPOINTS)
    assert re.search(r'knowledge: "/knowledge/sources"', read(ENDPOINTS))
    assert "interview: (id: string) => `/interview/sessions/${seg(id)}`" in read(ENDPOINTS)


def test_the_session_mapper_asks_the_name_its_record_declares_first():
    """Order is the whole difference between a badge and no badge.

    `positionTitle` is the component; `jobTitle`, `job_title` and `position` were names the frontend
    invented, and a list that asked one of them first showed no role for every session.
    """
    body = mapper_body("mapSessionScalars")
    job_title = next(lit for _, _, lit in reader_calls("mapSessionScalars") if "positionTitle" in lit)
    assert job_title[0] == "positionTitle", job_title
    assert job_title == ["positionTitle", "position_title", "jobTitle", "job_title", "position"], \
        job_title
    assert "no producer" not in body
    authored = set(record_components("SessionItem"))
    assert "positionTitle" in authored and "jobTitle" not in authored
    assert job_title[2:] == ["jobTitle", "job_title", "position"], \
        "the invented aliases moved; the comment above them explains why they are not the first term"
    detail = mapper_body("mapInterviewSessionDetail")
    assert "...mapSessionScalars(sess)" in detail and "...mapSessionScalars(s)" in \
        mapper_body("mapInterviewSessionItem"), "the scalar mapper is no longer the shared reader"
    # The detail mapper inherits the scalars by spreading them, so it never re-asks an invented
    # alias: the one `jobTitle` a detail payload can carry comes from the shared reader above.
    assert "jobTitle" not in detail


def test_the_company_research_columns_round_trip_through_every_layer():
    """The researched profile is an answer now, not a write-only hole.

    `culture`, `interviewProcess` and `sources` were accepted by the request, stored on the row, and
    dropped by every read path -- a profile could be posted and never seen again. The read record
    carries all three now, the item builder passes them, the mapper asks them first, and the detail
    screen reads them, so the round trip is one pin across all four layers.
    """
    request = set(record_components("CompanyRequest"))
    item = set(record_components("CompanyItem"))
    researched = {"culture", "interviewProcess", "sources"}
    assert researched <= request, sorted(request)
    assert researched <= item, "the read record dropped a field it used to carry; re-measure"
    service = java("com/careeros/job/service/JobService.java")
    assert "company.setCulture(request.culture())" in service
    assert "company.setInterviewProcess(request.interviewProcess())" in service
    builder = function_body(service, "private static CompanyItem toCompanyItem(")
    for getter in ("getCulture", "getInterviewProcess", "getSources"):
        assert getter in builder, f"toCompanyItem stopped passing {getter}: {builder}"
    entity = java("com/careeros/job/entity/Company.java")
    assert '@Column(name = "culture")' in entity and '@Column(name = "interview_process")' in entity
    resources = read(RESOURCES)
    assert "culture" in CALLED[("mapCompany", "raw")]
    assert "interviewProcess" in CALLED[("mapCompany", "raw")]
    assert "sources" in CALLED[("mapCompany", "raw")]
    assert resources.count("api.post<unknown>(endpoints.companies") == 0, \
        "the app writes companies directly now; the write path this pins has a second front door"


def test_the_screens_read_their_mapper_output_and_only_the_versions_row_asks_dead_names():
    """Blast radius, per screen: which mapper output fields a page actually touches.

    The versions row reads `isCurrent` and `versionNo`, and both calls can never fire; the screen
    still works because each has a second term that is real. The companies page reads
    `openRoleCount`, which the item record has authored since the detail screen existed. The other
    surfaces read nothing their record does not author.
    """
    page = read(VERSIONS_PAGE)
    assert page.count("(versionsQ.data ?? []).map((v) =>") == 1
    arrow = page.index("(versionsQ.data ?? []).map((v) =>")
    body = page[arrow:balanced(page, page.index("{", arrow), "{", "}") + 1]
    reads = dotted_reads(body, "v")
    assert reads == VERSION_ROW_READS, sorted(reads)
    authored = set(record_components("ResumeVersionItem"))
    assert reads - authored == {"isCurrent", "versionNo", "source"}, sorted(reads - authored)
    assert "const isCurrent = v.isCurrent || v.id === r.currentVersionId;" in page
    assert "Version ${v.versionNo ?? v.id.slice(0, 8)}" in page
    assert "v.structured" not in page, "a screen now reads the field no version record declares"
    assert "currentVersionId" in set(record_components("ResumeListItem")), \
        "the term that carries the badge stopped being authored"

    companies = read(COMPANIES_PAGE)
    assert dotted_reads(companies, "c") == COMPANY_PAGE_READS, \
        sorted(dotted_reads(companies, "c") ^ COMPANY_PAGE_READS)
    assert dotted_reads(read(KNOWLEDGE_PAGE), "s") == KNOWLEDGE_PAGE_READS
    assert dotted_reads(read(INTERVIEWS_PAGE), "s") == INTERVIEWS_PAGE_READS
    # Two of those surfaces read only names their record authors; the interviews page reads the one
    # name the session mappers invent for their output (`jobTitle`), which is why the order case
    # above binds the alias list rather than the output key.
    assert COMPANY_PAGE_READS <= set(record_components("CompanyItem")), \
        sorted(COMPANY_PAGE_READS - set(record_components("CompanyItem")))
    assert KNOWLEDGE_PAGE_READS <= set(record_components("SourceItem")), \
        sorted(KNOWLEDGE_PAGE_READS - set(record_components("SourceItem")))
    assert INTERVIEWS_PAGE_READS - set(record_components("SessionItem")) == {"jobTitle"}, \
        sorted(INTERVIEWS_PAGE_READS - set(record_components("SessionItem")))

    # The same page that hosts the versions list also reads the detail body. The "Original file"
    # affordance used to read two names no producer sent (#155's dead conditional); it reads the
    # key the record actually authors now, and the route the key promises bytes from is served.
    detail_reads = dotted_reads(page, "r")
    assert detail_reads == RESUME_DETAIL_READS, sorted(detail_reads ^ RESUME_DETAIL_READS)
    assert detail_reads - set(record_components("ResumeDetail")) == set(), \
        "the detail screen reads a name its record does not declare"
    assert "r.sourceFileKey && (" in page, "the affordance moved; re-measure this claim"
    assert "downloadOriginal(r.id" in page, "the affordance is no longer wired to the download"
    assert "sourceFileKey" in set(record_components("ResumeDetail")), \
        "the name the detail record does author stopped being authored"


def test_the_dead_names_spread_in_three_measured_tiers_and_three_reached_a_screen():
    """Blast radius of a name no record authors, spelled out over the whole frontend census.

    The population is every `*.ts*` file under `frontend/src` (137 at this plane); the spellings
    walked are the 56 names the eight mappers ask for that their record declares in no spelling, and
    a camel name and its snake twin are separate entries. Twenty-eight of them live in three files
    or fewer, and those 28 are classified by exactly which files; beyond that a generic name (`name`,
    `score`, `title`) means something else in the file that spells it, so the census stops rather
    than pretend. The tier worth a decision is the one a screen belongs to: the versions row reads
    `isCurrent` and `versionNo`, both calls dead, the badge alive on a second real term.
    """
    files = frontend_files()
    # 160 rather than 158 since the profile editor's target-list guard joined with its own test
    # (`lib/profile-targets.ts` and `lib/profile-targets.test.ts`: the module the settings page
    # consults before it submits a target it is about to be told is not in the target list -- #216's
    # front-end half, `docs/profile-title-reuse.md` still describing the older raw-array shape).
    # 158 rather than 157 since the global-error boundary joined (app/global-error.tsx:
    # the shell the app renders when the root layout itself throws -- own <html>/<body>
    # and globals.css import, because no parent stylesheet survives that swap).
    # 157 rather than 156 since the (app) route-segment loading fallback joined
    # (app/(app)/loading.tsx: the skeleton the router shows while the next page's
    # chunk is in flight, the one gap the pages' own react-query skeletons miss).
    # 156 rather than 154 since the global not-found and error boundaries joined (app/not-found.tsx
    # and app/error.tsx: the 404 page and the client error screen the app fell back to Next's
    # unstyled defaults without).
    # 154 rather than 138 since the sixteen per-route metadata layouts joined (one small
    # layout.tsx per (app) route segment: the pages are client components and cannot export
    # metadata themselves, so each segment got a server layout that only names the tab title).
    # 138 rather than 137 since `components/jobs/import-job-dialog.tsx`, the paste-a-posting
    # importer on the jobs page; 137 rather than 136 since `components/settings/profile-cards.tsx`,
    # the settings page's career-profile editor; 136 rather than 135 since the knowledge page's
    # notes panel component joined. (Spell the panel's path out nowhere here -- the notes-route
    # census counts every mention of it, this file included.)
    assert len(files) == 160, f"the frontend census walked {len(files)} files"
    asked = {name for row in UNAUTHORED.values() for name in row}
    assert len(asked) == 56, f"{len(asked)} dead names are asked, pinned 56"
    classified = set()
    for carriers, names in DEAD_NAME_TIERS.items():
        for name in sorted(names):
            found = carriers_of(name)
            assert found == set(carriers), f"{name} is now spelled in {sorted(found ^ set(carriers))}"
            classified.add(name)
    assert len(classified) == 28, f"{len(classified)} names classified, pinned 28"
    assert len(asked) - len(classified) == WIDER_DEAD_NAMES, \
        f"{len(asked) - len(classified)} names spread past three carriers, pinned {WIDER_DEAD_NAMES}"
    assert classified <= asked

    # The mapper-only tier is the alias-list bloat: no module other than the one asking has the name.
    assert DEAD_NAME_TIERS[("lib/hooks/resources.ts",)] > {"file_name", "version_no", "is_current",
                                                           "chunk_count", "job_title"}, \
        "a snake twin left the mapper, so it is a name in use somewhere"
    # The types.ts mirror is a type that copies the ask, not a reader of the answer.
    assert DEAD_NAME_TIERS[("lib/api/types.ts", "lib/hooks/resources.ts")] == TYPES_MIRROR_NAMES
    read_by_a_screen = (VERSION_ROW_READS | RESUME_DETAIL_READS
                        | set().union(*READERS_BY_PAGE.values()))
    assert TYPES_MIRROR_NAMES & read_by_a_screen == set(), \
        sorted(TYPES_MIRROR_NAMES & read_by_a_screen)
    # The screen tier is the versions row's pair. `fileName` left this tier twice over: the detail
    # screen stopped reading it when the download went live, and what remains spelled is the
    # mapper's own title alias plus a React state name in source-actions.tsx -- a two-file tier.
    screen_tier = DEAD_NAME_TIERS[("app/(app)/resumes/[id]/page.tsx", "lib/api/types.ts",
                                   "lib/hooks/resources.ts")]
    assert screen_tier == SCREEN_READ_NAMES, sorted(screen_tier ^ SCREEN_READ_NAMES)
    assert SCREEN_READ_NAMES <= read_by_a_screen
    assert VERSION_ROW_READS >= {"isCurrent", "versionNo"}
