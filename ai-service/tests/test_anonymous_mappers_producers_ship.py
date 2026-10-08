"""#193: the six inline arrow mappers in `resources.ts`, bound to the producers that answer them.

#192 census the seven `function mapX` declarations and pinned that the same file holds exactly six
inline arrow mappers -- object literals passed straight to `normalizePage` (or to a `.map`) inside a
query hook -- which that file deliberately left out. This file binds those six, plus the four hooks
that pass them, to the route each hook calls and the Java that answers it.

What the six turn out to be is not the same shape as the named half. Three of the four hooks are live
screens (`useSavedJobs` on /jobs, `useConversations` on /copilot, `useKnowledgeNotes` through the
knowledge page's notes panel) and their rows are mostly honest:
the note row asks sixteen names and `NoteItem` answers six of them, `ConversationItem` answers
every *primary* ask and the copilot screen reads five of the seven authored names. One hook is a
bare-list route: `GET /jobs/saved` answers `List<SavedJobItem>`, so `normalizePage` takes its array
branch and the four page-envelope names are dead there exactly as they are on the versions row --
and `SavedJobItem` ships `note` and `savedAt`, which the row reaches through nobody: `normalizeJob`
unwraps `job` and stops, and no file under `frontend/src` reads `.savedAt` at all.

The fourth was the finding, and #226 fixed it. `useAIUsage` targets `/ai-usage/summary`, whose
handler builds a `Map<String, Object>` by hand and emits exactly eight keys; the hook used to ask
thirty names of that object -- a second-unwrap probe (`summary`/`data`) that could never fire,
three breakdown rows (`byAgent`, `byModel`, `daily`) no producer authors, and twenty-four dead
aliases spread across every reader call. The hook now asks the three of the eight the dashboard's
"Agent spend" card actually shows -- `requests`, `totalTokens` and `costUsd` -- each in the
handler's own spelling; no alias chain survives. The five columns nothing renders yet
(`inputTokens`, `outputTokens`, `cachedTokens`, `perModel`, `runsByStatus`) are declared in
EMITTED_UNASKED rather than asked for. `perModel` is worth knowing about: it is an object keyed
by model name, and the deleted `byModel` row could never have carried those names -- `list`
returns `Object.values` for a keyed map, so a future breakdown UI needs an entries-reader, not
this hook. The hook has a caller now: the dashboard's "Agent spend" card mounts `useAIUsage` and
reads those three numbers off it, and `useKnowledgeNotes` left the no-caller set too when the
knowledge page's notes panel mounted it and `useNoteMutations`, so all four hooks reach a screen
now. The `AIUsageSummary` interface that mirrors the mapper's shape is still named only in
`types.ts`.
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
CLIENT = FRONT / "lib" / "api" / "client.ts"
TYPES = FRONT / "lib" / "api" / "types.ts"
COPILOT = FRONT / "app" / "(app)" / "copilot" / "page.tsx"
JOBS_PAGE = FRONT / "app" / "(app)" / "jobs" / "page.tsx"
NAMED_GATE = TESTS / "test_resources_mapper_records_ship.py"

API_PREFIX = "/api/v1"

RECORD_FILES = {
    "SavedJobItem": "com/careeros/job/dto/JobDtos.java",
    "NoteItem": "com/careeros/knowledge/dto/KnowledgeDtos.java",
    "ConversationItem": "com/careeros/conversation/dto/ConversationDtos.java",
}
ACTIVITY_FILE = "com/careeros/activity/web/ActivityController.java"

# The population #192 counted and did not bind, in source order: (the hook that passes it, the
# receiver the arrow names). `j` is a spread, not a reader census -- see SITES below.
# #226 deleted `useAIUsage`'s three breakdown arrows (`a`/`m`/`d`): two asked for lists no
# producer authors, and the third rebuilt a keyed map's values through `list`, losing the names.
SITES = [("useSavedJobs", "j"), ("useKnowledgeNotes", "n"), ("useConversations", "c")]

# Every receiver this file walks, including the one that is not an arrow site: `raw` is
# `useAIUsage`'s response object (the second-unwrap probe went with #226), `j` is the saved row.
RECEIVERS = [("useSavedJobs", "j"), ("useKnowledgeNotes", "n"), ("useConversations", "c"),
             ("useAIUsage", "raw")]

HOOK_ROUTES = {
    "useSavedJobs": "savedJobs",
    "useKnowledgeNotes": "knowledgeNotes",
    "useConversations": "conversations",
    "useAIUsage": "aiUsage",
}

# Measured from the annotations: client path -> (verb, return type, handler, controller).
ROUTES = {
    "savedJobs": ("Get", "List<SavedJobItem>", "saved", "com/careeros/job/web/JobController.java"),
    "knowledgeNotes": ("Get", "PageDTO<NoteItem>", "notes",
                       "com/careeros/knowledge/web/KnowledgeController.java"),
    "conversations": ("Get", "PageDTO<ConversationItem>", "list",
                      "com/careeros/conversation/web/ConversationController.java"),
    "aiUsage": ("Get", "Map<String, Object>", "usageSummary", ACTIVITY_FILE),
}

# receiver -> the producer whose names answer its asks.
PRODUCER = {
    ("useSavedJobs", "j"): "SavedJobItem",
    ("useKnowledgeNotes", "n"): "NoteItem",
    ("useConversations", "c"): "ConversationItem",
    ("useAIUsage", "raw"): "usageSummary",
}

# Measured at this plane: one entry per reader call, in source order, keyed by the receiver it names.
# `idStr(x)` counts as a call for the one name its own declaration parses.
ASKS = {
    ("useSavedJobs", "j"): [],
    ("useKnowledgeNotes", "n"): [["id"], ["title", "name"], ["content", "body", "text"],
                                 ["kind", "type"], ["tags", "labels"],
                                 ["sourceId", "source_id"], ["createdAt", "created_at"],
                                 ["updatedAt", "updated_at"]],
    ("useConversations", "c"): [["id"], ["title", "name"], ["updatedAt", "updated_at"],
                                ["createdAt", "created_at"],
                                ["lastMessagePreview", "preview", "lastMessage"],
                                ["messageCount", "message_count"]],
    ("useAIUsage", "raw"): [["requests"], ["totalTokens"], ["costUsd"]],
}

# The other end of every row: pinned here and re-derived from the Java by the cases below.
SAVED_JOB_ITEM = ["job", "note", "savedAt"]
NOTE_ITEM = ["id", "title", "content", "tags", "createdAt", "updatedAt"]
CONVERSATION_ITEM = ["id", "title", "context", "createdAt", "updatedAt", "lastMessagePreview",
                     "messageCount"]
USAGE_KEYS = ["inputTokens", "outputTokens", "cachedTokens", "totalTokens", "costUsd", "requests",
              "perModel", "runsByStatus"]
PER_MODEL_KEYS = ["inputTokens", "outputTokens", "cachedTokens", "costUsd", "requests"]
PER_MODEL_HOLDER = "LinkedHashMap"

PAGE_ENVELOPE = ["items", "total", "page", "size"]

# Dead = asked here, authored by this receiver's producer nowhere. UNAUTHORED = dead here *and* no
# response in the backend authors that spelling, so no route this app can call would ever answer it.
DEAD = {
    ("useSavedJobs", "j"): set(),
    ("useKnowledgeNotes", "n"): {"body", "created_at", "kind", "labels", "name", "sourceId",
                                 "source_id", "text", "type", "updated_at"},
    ("useConversations", "c"): {"created_at", "lastMessage", "message_count", "name", "preview",
                                "updated_at"},
    ("useAIUsage", "raw"): set(),
}
UNAUTHORED = {
    ("useSavedJobs", "j"): set(),
    ("useKnowledgeNotes", "n"): {"body", "created_at", "labels", "source_id", "updated_at"},
    ("useConversations", "c"): {"created_at", "message_count", "preview", "updated_at"},
    ("useAIUsage", "raw"): set(),
}

# What the summary emits that this hook never asks: the input/output/cached token columns, the
# per-model breakdown (`perModel`, an object keyed by model name -- `list` would return its values
# and lose the names, so a future breakdown UI needs an entries-reader, not this hook), and the
# runs-by-status map.
EMITTED_UNASKED = {"cachedTokens", "inputTokens", "outputTokens", "perModel", "runsByStatus"}

# (hook, receiver) -> (call count, name count). Derived by the scanner below and pinned so a
# narrowed scan, a lost import alias or a moved call has to be reconciled, not absorbed.
SCANNER_SHAPE = {
    ("useSavedJobs", "j"): (0, 0),
    ("useKnowledgeNotes", "n"): (8, 16),
    ("useConversations", "c"): (6, 12),
    ("useAIUsage", "raw"): (3, 3),
}

READER_VOCABULARY = {"list": "listOf", "pick": "pick", "str": "str", "num": "num",
                     "strList": "strList"}

# Which files outside resources.ts name a hook (the reach), and what those screens read.
CALLERS = {
    "useSavedJobs": ["app/(app)/jobs/page.tsx"],
    "useConversations": ["app/(app)/copilot/page.tsx"],
    "useKnowledgeNotes": ["components/knowledge/notes-panel.tsx"],
    "useAIUsage": ["app/(app)/dashboard/page.tsx"],
}
COPILOT_READS = {"createdAt", "id", "lastMessagePreview", "title", "updatedAt"}
JOBS_SAVED_READS = {"items", "total"}


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
    """Split on commas that are outside brackets, angles and quotes."""
    inner = text[open_at + 1:balanced(text, open_at, "(", ")")]
    parts, buf, depth, quote, previous = [], "", 0, None, ""
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


def function_body(text: str, declaration: str) -> str:
    at = text.index(declaration)
    params_end = balanced(text, text.index("(", at), "(", ")") + 1
    brace = text.index("{", params_end)
    return text[at:balanced(text, brace, "{", "}") + 1]


def record_components(name: str) -> list[str]:
    text = java(RECORD_FILES[name])
    at = text.index(f"record {name}")
    return [a.split()[-1] for a in top_level_args(text, text.index("(", at))]


def hook_body(name: str) -> str:
    return function_body(read(RESOURCES), f"export function {name}(")


def idstr_asks() -> list[str]:
    """The names `idStr` reads, parsed out of its own declaration rather than assumed."""
    declaration = re.search(r"^const idStr = .*$", read(RESOURCES), re.M).group(0)
    return [m.group(1) for m in re.finditer(r'pick\(raw,\s*"([^"]+)"', declaration)]


def reader_vocabulary() -> dict[str, str]:
    """Reader names resources.ts can call, resolved through the file's own import aliases.

    `list as listOf` is why this cannot be a hand-typed list: the file calls `listOf`, and a census
    that looked for `list(` would report that these rows never read a list at all.
    """
    exported = set(re.findall(
        r"^export function (\w+)(?:<[^>]*>)?\(obj: unknown, \.\.\.\w+: string\[\]",
        read(NORMALIZE), re.M))
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


def calls_for(hook: str) -> dict[str, list[list[str]]]:
    """Every reader call in a hook body, grouped by the receiver it names, in source order.

    Nested calls count: the three breakdown rows sit inside `.map((a) => ({...}))` in the same body
    as the top-level object, and a scanner that stopped at the first nesting level would classify
    `useAIUsage` as one row of nine names instead of four rows of thirty-plus. `idStr` is walked
    with the readers because it is a reader -- it just takes its one name from its own declaration
    instead of from the call site.
    """
    body = hook_body(hook)
    vocabulary = "|".join(re.escape(local) for local in sorted(set(reader_vocabulary().values())))
    pattern = r"(?<![\w$.])(?:%s|idStr)\s*(?:<[^>]*>)?\(" % vocabulary
    grouped: dict[str, list[list[str]]] = {}
    for match in re.finditer(pattern, body):
        args = top_level_args(body, body.index("(", match.end() - 1))
        receiver = args[0].strip()
        if body[match.start():match.start() + 6] == "idStr(":
            names = list(idstr_asks())
        else:
            names = [m.group(1) for arg in args[1:] if (m := re.fullmatch(r'"([^"]*)"', arg))]
        grouped.setdefault(receiver, []).append(names)
    return grouped


def response_names() -> set[str]:
    """Every name a backend response can carry: record components plus literal map keys.

    Deliberately not `@Column(name = ...)` -- those are database spellings, and they only reach the
    wire through a record component or a literal `put`, which is what this census looks for.
    """
    names: set[str] = set()
    for path in JAVA.rglob("*.java"):
        text = read(path)
        for match in re.finditer(r"\brecord\s+(\w+)\s*(?:<[^>]*>)?\s*\(", text):
            for arg in top_level_args(text, match.end() - 1):
                if arg.strip():
                    names.add(arg.strip().split()[-1])
        names.update(re.findall(r'\.put\("([^"]+)"', text))
        names.update(re.findall(r'Map\.of\("([^"]+)"', text))
    return names


def spring_routes() -> dict[str, list[tuple[str, str, str, str]]]:
    """Full path -> [(verb, return type, handler, controller)] from every @RestController."""
    found: dict[str, list[tuple[str, str, str, str]]] = {}
    for path in sorted(JAVA.rglob("*.java")):
        text = read(path)
        if "@RestController" not in text:
            continue
        base = re.search(r'@RequestMapping\("([^"]*)"\)', text)
        prefix = base.group(1) if base else ""
        for match in re.finditer(r'@(Get|Post|Patch|Put|Delete)Mapping(?:\("([^"]*)"\))?'
                                 r"\s*\n\s*(?:@\w[^\n]*\n\s*)*(?:public\s+)?"
                                 r"([\w<>, ?.]+)\s+(\w+)\(", text):
            verb, sub, ret, handler = match.groups()
            found.setdefault(prefix + (sub or ""), []).append(
                (verb, ret.strip(), handler, str(path.relative_to(JAVA)).replace("\\", "/")))
    return found


def emitted_usage_keys() -> list[str]:
    body = function_body(java(ACTIVITY_FILE), "public Map<String, Object> usageSummary(")
    return re.findall(r'result\.put\("([^"]+)"', body)


def per_model_keys() -> list[str]:
    body = function_body(java(ACTIVITY_FILE), "public Map<String, Object> usageSummary(")
    at = body.index("perModel.put(")
    map_of = body.index("Map.of(", at)
    args = top_level_args(body, body.index("(", map_of))
    assert len(args) % 2 == 0, f"a Map.of(...) with {len(args)} arguments is not a key/value list"
    return [a.strip('"') for a in args[0::2]]


def frontend_files() -> list[str]:
    return sorted(str(p.relative_to(FRONT)).replace("\\", "/") for p in FRONT.rglob("*.ts*"))


def carriers(token: str) -> list[str]:
    return [rel for rel in frontend_files() if re.search(r"\b" + token + r"\b", read(FRONT / rel))]


def dotted_reads(text: str, variable: str) -> set[str]:
    return {m.group(1) for m in re.finditer(r"(?<![\w$.])" + re.escape(variable) + r"\.(\w+)", text)}


def test_the_three_inline_sites_are_the_half_the_named_mapper_census_leaves_out():
    """Two files, one population each, and neither may absorb the other's rows.

    #192 pinned `len(anonymous) == 6` without binding them, and #226 deleted the three
    `useAIUsage` breakdown arrows, so the pin is 3 now. This file binds the sites; the pin and
    this population have to stay the same number, and the two files must not name the same
    receiver, or the same dead alias gets two owners and reconciles twice.
    """
    text = read(RESOURCES)
    receivers = [m.group(1) for m in re.finditer(r"\((\w+)\) => \(\{", text)]
    assert receivers == [r for _, r in SITES], (
        f"the inline arrow population moved or changed shape: {receivers}")
    neighbour = read(NAMED_GATE)
    assert "len(anonymous) == %d" % len(SITES) in neighbour, (
        "test_resources_mapper_records_ship.py no longer pins the count this file owns; its "
        "population and this one are the same fact and have to be reconciled together")
    named_receivers = set(re.findall(r'\("map\w+", "(\w)"\)', neighbour))
    assert not named_receivers & set(receivers), (
        f"receivers {sorted(named_receivers & set(receivers))} are bound by both files")
    for hook, receiver in SITES:
        assert re.search(r"\(" + receiver + r"\) => \(\{", hook_body(hook)), (
            f"the site for {receiver} is no longer inside {hook}")


def test_each_site_is_named_by_the_endpoint_its_hook_calls():
    """The hook -> endpoint-key -> client-path chain is read from the shipped files."""
    endpoint_text = read(ENDPOINTS)
    for hook, key in HOOK_ROUTES.items():
        used = re.findall(r"endpoints\.(\w+)", hook_body(hook))
        assert used == [key], f"{hook} calls {used}, expected exactly [{key}]"
        declared = re.findall(r"^\s+" + key + r': "([^"]*)"', endpoint_text, re.M)
        assert len(declared) == 1, f"{key} is declared {len(declared)} times in endpoints.ts"
        assert declared[0].startswith("/"), f"{key} is not a rooted path: {declared[0]}"


def test_the_four_routes_are_read_from_the_annotation_that_answers_them():
    """Each client path resolves to exactly one GET mapping, whose declared return type is pinned."""
    routes = spring_routes()
    for hook, key in HOOK_ROUTES.items():
        path = re.search(r'\s+' + key + r': "([^"]*)"', read(ENDPOINTS)).group(1)
        hits = routes.get(API_PREFIX + path, [])
        gets = [entry for entry in hits if entry[0] == "Get"]
        assert len(gets) == 1, f"{path} resolves to {hits}, not one GET"
        assert tuple(gets[0]) == ROUTES[key], (
            f"the handler behind {path} changed: {gets[0]} != {ROUTES[key]}")


def test_the_usage_hook_does_not_re_unwrap_the_envelope_the_client_already_unwrapped():
    """`pick(raw, "summary", "data")` was a second unwrap of a body that was unwrapped once.

    The advice wraps every handler's answer in `{success, data, error}` and `request()` hands back
    `json.data`, so the mapper's receiver is already the handler's own object and the probe could
    never fire. #226 deleted it; this case pins the mechanism that made it dead, and its absence.
    """
    client = read(CLIENT)
    assert re.search(r"return \(json\?\.data \?\? \(null as T\)\) as T;", client), (
        "request() no longer unwraps the envelope, so a mapper's receiver is no longer the "
        "handler's own object and this classification has to be re-derived")
    envelope = re.search(r"\{\"success\":true,\"data\":", java("com/careeros/common/ApiResponse.java"))
    assert envelope, "ApiResponse's own docstring no longer names the envelope it writes"
    body = hook_body("useAIUsage")
    assert "pick(" not in body, (
        "the usage hook re-unwraps the envelope; the probe can never fire and asks names "
        "(summary, data) the handler does not emit")
    names = calls_for("useAIUsage")["raw"]
    assert names == ASKS[("useAIUsage", "raw")]
    for name in ("summary", "data"):
        assert name not in emitted_usage_keys(), (
            f"usageSummary now emits {name!r}, so the second unwrap would be live and the top-level "
            "receiver has to be reclassified")


def test_jobs_saved_answers_a_bare_list_so_the_page_envelope_names_are_dead_there():
    """The array branch of normalizePage is the only reachable one on this route.

    `ret` is read off the annotation by the same walk case 3 uses, not out of this file's own table:
    the whole claim is about what the handler declares, and a table re-asserting itself would stay
    green while the Java moved.
    """
    path = re.search(r'\s+savedJobs: "([^"]*)"', read(ENDPOINTS)).group(1)
    gets = [entry for entry in spring_routes()[API_PREFIX + path] if entry[0] == "Get"]
    assert len(gets) == 1, f"{path} resolves to {gets}, not one GET"
    ret = gets[0][1]
    assert ret == "List<SavedJobItem>", f"/jobs/saved now answers {ret}"
    assert ROUTES["savedJobs"][1] == ret, "this file's route table and the shipped annotation disagree"
    page = function_body(read(NORMALIZE), "export function normalizePage<T>(")
    assert re.search(r"if \(Array\.isArray\(raw\)\) \{\n\s*return \{ items: raw\.map\(map\)", page), (
        "normalizePage no longer short-circuits on an array, so a bare List is read as an object "
        "and the envelope names below become live")
    assert "PageDTO" not in ret
    for name in PAGE_ENVELOPE:
        assert name not in record_components("SavedJobItem"), (
            f"SavedJobItem now ships {name!r}; the page shape would be reachable under the wrapper")
    jobs = read(JOBS_PAGE)
    assert {m.group(1) for m in re.finditer(r"saved\.data\??\.(\w+)", jobs)} == JOBS_SAVED_READS, (
        "the saved tab reads a different pair off the page object than this file describes")


def test_savedjobitem_ships_three_names_and_the_row_reaches_one():
    """The bookmark note and timestamp are authored, shipped and read by nobody."""
    assert record_components("SavedJobItem") == SAVED_JOB_ITEM
    assert calls_for("useSavedJobs").get("j", []) == []
    normalize_job = function_body(read(NORMALIZE), "export function normalizeJob(")
    unwrap = re.findall(r'pick\(raw, "job", "data"\)', normalize_job)
    assert unwrap, "normalizeJob no longer unwraps the SavedJobItem wrapper, so every ask below " \
                   "would land on the wrapper instead of the job"
    for name in ("note", "savedAt"):
        assert f'"{name}"' not in normalize_job, (
            f"normalizeJob now reads {name!r}; the saved row reaches it and this claim is stale")
    assert sorted({m.group(0) for rel in frontend_files()
                   for m in re.finditer(r"\w+\.savedAt\b", read(FRONT / rel))}) == [], (
        "something reads `.savedAt` now; name the reader here before the field disappears again")
    note_readers = sorted(rel for rel in frontend_files()
                          if re.search(r"\.note\b", read(FRONT / rel)))
    assert "app/(app)/jobs/page.tsx" not in note_readers, (
        f"the saved tab reads a note now ({note_readers}); then the bookmark note is live and the "
        "row has to ask for it")


def test_noteitem_answers_six_names_and_the_note_row_asks_sixteen():
    """The note row is the best-behaved of the four, and still half of its asks can never fire."""
    assert record_components("NoteItem") == NOTE_ITEM
    grouped = calls_for("useKnowledgeNotes")
    assert [g for g in grouped["n"]] == ASKS[("useKnowledgeNotes", "n")]
    authors = set(NOTE_ITEM)
    asked = {name for call in grouped["n"] for name in call}
    assert asked - authors == DEAD[("useKnowledgeNotes", "n")], (
        f"the note row's dead asks are now {sorted(asked - authors)}")
    assert asked & authors == {"content", "createdAt", "id", "tags", "title", "updatedAt"}
    kinds = {name for name in DEAD[("useKnowledgeNotes", "n")]
             if name in response_names()}
    assert kinds == {"kind", "name", "sourceId", "text", "type"}, (
        f"{sorted(kinds)} joined or left the set of dead note names some other record authors")
    note_type = function_body(read(TYPES), "export interface KnowledgeNote {")
    for name in ("body", "kind", "sourceId"):
        assert re.search(r"^\s+" + name + r"\?:", note_type, re.M), (
            f"types.ts no longer declares {name!r} on KnowledgeNote, so the type stopped mirroring "
            "a name no producer authors -- or the mapper and the type were fixed together and this "
            "case has to follow")


def test_the_conversation_row_asks_twelve_and_six_screen_names_reach_the_copilot():
    assert record_components("ConversationItem") == CONVERSATION_ITEM
    grouped = calls_for("useConversations")
    assert [g for g in grouped["c"]] == ASKS[("useConversations", "c")]
    authors = set(CONVERSATION_ITEM)
    asked = {name for call in grouped["c"] for name in call}
    assert asked - authors == DEAD[("useConversations", "c")]
    assert asked & authors == {"createdAt", "id", "lastMessagePreview", "messageCount", "title",
                               "updatedAt"}
    assert "context" not in asked, "the row now reads the conversation context; reclassify it"
    copilot = read(COPILOT)
    assert dotted_reads(copilot, "c") == COPILOT_READS, (
        f"the copilot list reads {sorted(dotted_reads(copilot, 'c'))} off a conversation row; this "
        "file says which of them the mapper actually fills")
    assert "messageCount" not in dotted_reads(copilot, "c"), (
        "the digest count has a reader now -- it was asked-and-never-shown when this was measured")


def test_ai_usage_summary_emits_eight_keys_and_the_hook_asks_three_of_them():
    """The headline: a hand-built map with eight keys against a reader that asked for thirty.

    #226 deleted twenty-seven of the thirty asks -- the dead aliases and the three breakdown rows
    -- along with the envelope probe's two. The three that remain are the ones the spend card
    shows, each in the handler's own spelling; the five emitted columns nothing renders are
    declared in EMITTED_UNASKED, not asked for.
    """
    emitted = emitted_usage_keys()
    assert emitted == USAGE_KEYS, f"usageSummary now writes {emitted}"
    grouped = calls_for("useAIUsage")
    assert [g for g in grouped["raw"]] == ASKS[("useAIUsage", "raw")]
    asked = {name for call in grouped["raw"] for name in call}
    assert asked == {"costUsd", "requests", "totalTokens"}, (
        f"the usage hook now answers {sorted(asked)} off the summary")
    assert asked - set(emitted) == DEAD[("useAIUsage", "raw")] == set(), (
        f"dead asks are now {sorted(asked - set(emitted))}")
    assert set(emitted) - asked == EMITTED_UNASKED, (
        f"the summary emits {sorted(set(emitted) - asked)} that this hook never asks; the "
        "cached-token column #67 exists to count is among them")


def test_the_one_breakdown_the_summary_emits_is_keyed_by_model_name():
    """`perModel` has a real author; the rows #226 deleted could never have carried its names.

    The handler puts a `Map.of(...)` under the model name, so `list` would return the values and
    lose the names -- a future breakdown UI needs an entries-reader, and this case pins the shape
    that reader will consume, that nothing asks it yet, and that EMITTED_UNASKED says so.
    """
    assert per_model_keys() == PER_MODEL_KEYS
    body = function_body(java(ACTIVITY_FILE), "public Map<String, Object> usageSummary(")
    assert f"Map<String, Object> perModel = new {PER_MODEL_HOLDER}<>()" in body
    assert re.search(r"perModel\.put\(model, Map\.of\(", body), (
        "perModel is no longer keyed by model name, so the breakdown shape EMITTED_UNASKED "
        "declares has changed")
    asked = {name for call in ASKS[("useAIUsage", "raw")] for name in call}
    assert "perModel" not in asked, (
        "the hook asks the breakdown now; give it an entries-reader first, and reconcile this "
        "case and EMITTED_UNASKED")
    assert "perModel" in EMITTED_UNASKED, (
        "the breakdown is declared unread; this case and EMITTED_UNASKED have to be reconciled")


def test_a_dead_name_here_is_either_another_records_author_or_no_ones_at_all():
    """Two classes of dead, told apart by a census of every name a response can carry.

    The census is record components plus literal map keys, and it is what separates `sourceId` (a
    name `TextIngestResponse` really ships, just not on this route) from `labels` (a name this
    repository has never put on a response). The floor proves the census read something: an empty
    or narrowed walk would make every dead name look unauthored and this case would pass on nothing.
    """
    names = response_names()
    assert len(names) > 200, f"the response-name census read only {len(names)} names"
    assert "created_at" not in names, (
        "a snake_case spelling entered the response census; either a producer started emitting it "
        "or the walk started reading @Column names, which are not wire names")
    for key, dead in DEAD.items():
        asked = {name for call in ASKS[key] for name in call}
        assert asked - produced_by(key) == dead, (
            f"{key}: dead asks are now {sorted(asked - produced_by(key))}, pinned {sorted(dead)}")
        assert dead - names == UNAUTHORED[key], (
            f"{key}: unauthored names are now {sorted(dead - names)}")


def test_every_hook_is_named_by_the_screen_that_mounts_it():
    """No hook in `resources.ts` is named only at its own definition any more.

    `useAIUsage` was the last one until the dashboard's spend card mounted it and #226 bound its
    asks to the summary's own keys, which is exactly the class the old no-caller case existed to
    distinguish; `useKnowledgeNotes` joined the mounted side when the knowledge page grew its notes
    panel, so the no-caller class is empty and this case pins each hook's carrier set instead.
    """
    for hook, expected in CALLERS.items():
        found = [rel for rel in carriers(hook) if rel != "lib/hooks/resources.ts"]
        assert found == expected, f"{hook} is now named by {found}, expected {expected}"
        assert "lib/hooks/resources.ts" in carriers(hook), f"{hook} left the file that defines it"
    assert carriers("AIUsageSummary") == ["lib/api/types.ts"], (
        f"AIUsageSummary is named by {carriers('AIUsageSummary')}; the interface stopped being an "
        "unread mirror of the mapper the dashboard's card reads through")
    summary = function_body(read(TYPES), "export interface AIUsageSummary {")
    asked = {name for call in ASKS[("useAIUsage", "raw")] for name in call[:1]}
    for name in sorted(asked):
        assert re.search(r"^\s+" + name + r"\?:", summary, re.M), (
            f"types.ts dropped {name!r} from AIUsageSummary while the mapper still asks it")


def test_the_scanner_sees_every_call_and_name_in_this_population():
    """The census itself, pinned: 17 calls and 31 names across four receivers, none absorbed."""
    vocabulary = reader_vocabulary()
    assert vocabulary == READER_VOCABULARY, (
        f"the reader vocabulary resources.ts can reach is now {vocabulary}; this file's scan is "
        "only as wide as that import block")
    assert idstr_asks() == ["id"], f"idStr now reads {idstr_asks()}; the rows' first ask changed"
    totals = {"calls": 0, "names": 0}
    for key in RECEIVERS:
        hook, receiver = key
        calls = calls_for(hook).get(receiver, [])
        shape = (len(calls), sum(len(c) for c in calls))
        assert shape == SCANNER_SHAPE[key], (
            f"{hook}/{receiver}: the scanner sees {shape[0]} calls and {shape[1]} names, pinned "
            f"{SCANNER_SHAPE[key][0]}/{SCANNER_SHAPE[key][1]}")
        totals["calls"] += shape[0]
        totals["names"] += shape[1]
    assert (totals["calls"], totals["names"]) == (17, 31), (
        f"the census is {totals}; every dead-name claim above is measured over these calls, so "
        "re-derive the tables before changing this number")


def produced_by(key):
    """The names this receiver's producer answers, derived from the Java rather than from a table."""
    hook, receiver = key
    producer = PRODUCER[(hook, receiver)]
    if producer in RECORD_FILES:
        return set(record_components(producer))
    if producer == "usageSummary":
        return set(emitted_usage_keys())
    return set()
