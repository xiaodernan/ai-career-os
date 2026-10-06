"""#195: the window each list screen asks for, and which of the three numbers decides it.

#194 asked what a screen does with the window the answer carries, and found `size` has zero readers.
This file asks the other side: what does the client put in the request, and is the number it put
there the one that arrives? Three numbers can decide a request window -- the literal written in the
query hook, the argument the screen passes to that hook, and the `defaultValue` on the controller's
`@RequestParam`. Only two of the three ever get spent, and the shipped text decides which per route.

Ten hooks hand `normalizePage` a request. Eight offer a `size` literal: resumes 20, jobs 20,
applications 50, companies 20, knowledge sources 50, knowledge notes 50, interviews 50,
conversations 50; `useSavedJobs` sends no window (its route binds none) and `useActivityRuns` sends
`{ limit: params?.limit }`, a number that stays out of the URL when the caller omits it. Walking
every shipped call site outside `resources.ts` finds the literal's own value decided elsewhere on
two routes and on a third never spent at all: `useJobs`'s two callers both carry a size (the jobs
board spreads its URL-backed `filters`, the dashboard passes `{ size: 3 }`), so the `20` at
`resources.ts:178` is shadowed on every path -- and the case over `useUrlState` shows the shadowing
cannot be avoided by a bad URL, because `hydrateState` seeds `{...initial}` and only overwrites a
numeric key when `asUrlNumber` yields an integer, so `filters.size` is 12 or an address-bar integer,
never absent. `useApplications` has one caller, `{ size: 100 }`, which buries its `50`.
`useKnowledgeNotes`'s one caller passes no arguments, so its `50` stands -- and reaches a wire now
that the knowledge page's notes panel mounts the hook.

The server's side of the same table: four of the eight literals agree with the route's own
`defaultValue` (resumes 20/20, companies 20/20, jobs 20/20, applications 50/50) and four overstate
it (knowledge sources, notes, interviews and conversations all ask 50 where the handler says 20), so
those four defaults are only ever spent by a request the app does not make. The two shadowed
literals sit in the agreeing half -- jobs 20 against a 20 default, applications 50 against a 50 one
-- which is why nothing on screen changes when they are unreachable: a redundant number cannot
contradict anything, and cannot be noticed either. The notes literal is in the other half (50
against a 20 default), so the one wire it now builds carries a number the server would never
have chosen.

The reachable numbers have consequences the screens do not cover. The applications board asks for
exactly `Paging.MAX_PAGE_SIZE` (100), which `Paging`'s own comment answers with "A caller wanting
more pages pages." -- and `<Pagination>` is written in one file app-wide, the jobs page, so the
applications screen renders no pager and reads no `total`: its 101st application is simply not there.
`useActivityRuns` is the one hook where the server still decides, because `client.ts` omits an
undefined param rather than sending the word, and the handler defaults `limit` to 30 through
`Paging.first`.

Nothing here is fixed: which number should win, and whether the applications board should page or
raise its ceiling are owner decisions. What lands is
the measurement -- per hook, per call site, per route -- from one walk of each of the three tables.
"""

import functools
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
URL_STATE = FRONT / "lib" / "hooks" / "use-url-state.ts"
JOBS_PAGE = FRONT / "app" / "(app)" / "jobs" / "page.tsx"
APPS_PAGE = FRONT / "app" / "(app)" / "applications" / "page.tsx"
PAGING = "com/careeros/common/Paging.java"
ACTIVITY = "com/careeros/activity/web/ActivityController.java"

API_PREFIX = "/api/v1"
MAX_PAGE_SIZE = 100

# Measured off this plane; case 1 re-derives every row from the hooks' own bodies.
WIRE = {
    "useResumes": ("resumes", "{ size: 20 }"),
    "useJobs": ("jobs", "{ size: 20, ...clean }"),
    "useSavedJobs": ("savedJobs", None),
    "useApplications": ("applications", "{ size: 50, ...(params ?? {}) }"),
    "useCompanies": ("companies", "{ size: 20, ...(params ?? {}) }"),
    "useKnowledgeSources": ("knowledge", "{ size: 50, documentId }"),
    "useKnowledgeNotes": ("knowledgeNotes", "{ size: 50 }"),
    "useInterviewSessions": ("interviews", "{ size: 50 }"),
    "useActivityRuns": ("activityRuns", "{ limit: params?.limit }"),
    "useConversations": ("conversations", "{ size: 50 }"),
}

# Measured call sites, one walk; case 3 re-derives them. `""` is a call with no arguments.
SITES = {
    "useResumes": [("app/(app)/dashboard/page.tsx", ""), ("app/(app)/jobs/page.tsx", ""),
                   ("app/(app)/resumes/page.tsx", "")],
    "useJobs": [("app/(app)/dashboard/page.tsx", "{ size: 3 }"),
                ("app/(app)/jobs/page.tsx",
                 'tab === "discover" ? filters : { size: filters.size, page: filters.page }')],
    "useSavedJobs": [("app/(app)/jobs/page.tsx", "")],
    "useApplications": [("app/(app)/applications/page.tsx", "{ size: 100 }")],
    "useCompanies": [("app/(app)/companies/page.tsx", "")],
    "useKnowledgeSources": [("app/(app)/knowledge/page.tsx", "true, src")],
    "useKnowledgeNotes": [("components/knowledge/notes-panel.tsx", "")],
    "useInterviewSessions": [("app/(app)/interviews/page.tsx", "")],
    "useActivityRuns": [("app/(app)/activity/page.tsx", ""),
                        ("app/(app)/dashboard/page.tsx", "{ limit: 5 }")],
    "useConversations": [("app/(app)/copilot/page.tsx", "")],
}

# route path -> the `defaultValue` on the handler's `int size` parameter, or None if it binds none.
SERVER_SIZE = {
    "/api/v1/resumes": "20",
    "/api/v1/jobs": "20",
    "/api/v1/jobs/saved": None,
    "/api/v1/applications": "50",
    "/api/v1/companies": "20",
    "/api/v1/knowledge/sources": "20",
    "/api/v1/knowledge/notes": "20",
    "/api/v1/interview/sessions": "20",
    "/api/v1/conversations": "20",
    "/api/v1/activity/runs": None,
}

# The hooks whose params object spells a numeric `size`.
SIZE_LITERAL = {
    "useResumes": 20,
    "useJobs": 20,
    "useApplications": 50,
    "useCompanies": 20,
    "useKnowledgeSources": 50,
    "useKnowledgeNotes": 50,
    "useInterviewSessions": 50,
    "useConversations": 50,
}


def read(path: Path) -> str:
    """Shipped text with LF endings; `git archive` hands out CRLF on this host."""
    return path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")


def java(rel: str) -> str:
    return read(JAVA / rel)


def collapse(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


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


def endpoint_path(key: str) -> str:
    declared = re.search(r"^\s+" + key + r': "([^"]*)"', read(ENDPOINTS), re.M)
    assert declared, f"endpoints.ts declares no {key!r}"
    return API_PREFIX + declared.group(1)


@functools.lru_cache(maxsize=None)
def spring_gets() -> dict[str, tuple[str, str, str, int]]:
    """Full path -> (return type, handler, controller, offset of the handler's `(`), one GET each."""
    found: dict[str, tuple[str, str, str, int]] = {}
    for path in sorted(JAVA.rglob("*.java")):
        text = read(path)
        if "@RestController" not in text:
            continue
        base = re.search(r'@RequestMapping\("([^"]*)"\)', text)
        prefix = base.group(1) if base else ""
        for match in re.finditer(r'@GetMapping(?:\("([^"]*)"\))?\s*\n'
                                 r"\s*(?:@\w[^\n]*\n\s*)*(?:public\s+)?"
                                 r"([\w<>, ?.]+)\s+(\w+)\(", text):
            sub, ret, handler = match.groups()
            full = prefix + (sub or "")
            assert full not in found, f"{full} is answered by two GETs: {found.get(full)} and {handler}"
            found[full] = (ret.strip(), handler, str(path.relative_to(JAVA)).replace("\\", "/"),
                           match.end() - 1)
    return found


def bound_ints(path: str) -> dict[str, str | None]:
    """parameter name -> its `defaultValue`, for every `int` the handler of `path` binds."""
    _, _, rel, at = spring_gets()[path]
    args = top_level_args(java(rel), at)
    out: dict[str, str | None] = {}
    for arg in args:
        named = re.search(r"\bint (\w+)$", collapse(arg))
        if named:
            default = re.search(r'defaultValue = "(-?\d+)"', collapse(arg))
            out[named.group(1)] = default.group(1) if default else None
    return out


def list_wires() -> dict[str, tuple[str, str | None]]:
    """hook -> (endpoint key, the params object literal it hands api.get), from the hook's own text.

    The population is `normalizePage`, not a name list: a hook that spends a page-shaped answer is a
    hook whose request window is decided somewhere, which is the question this file asks.
    """
    resources = read(RESOURCES)
    out: dict[str, tuple[str, str | None]] = {}
    for match in re.finditer(r"export function (use\w+)\(", resources):
        body = function_body(resources, match.group(0))
        if "normalizePage(" not in body:
            continue
        at = body.index("api.get<unknown>(endpoints.")
        keyed = re.match(r"api\.get<unknown>\(endpoints\.(\w+)", body[at:])
        assert keyed, f"{match.group(1)} calls api.get without an endpoints.* key"
        key = keyed.group(1)
        close = balanced(body, body.index("(", at), "(", ")")
        tail = body[at + len(f"api.get<unknown>(endpoints.{key}"):close].strip()
        params = collapse(tail[1:]) if tail.startswith(",") else None
        out[match.group(1)] = (key, params)
    return out


def call_sites(hook: str, include_tests: bool = False) -> list[tuple[str, str]]:
    """(file, collapsed arguments) for every call of `hook(` outside the hook file itself."""
    out = []
    for path in sorted(FRONT.rglob("*.ts*")):
        rel = str(path.relative_to(FRONT)).replace("\\", "/")
        if rel == "lib/hooks/resources.ts":
            continue
        if not include_tests and ".test." in rel:
            continue
        text = read(path)
        for match in re.finditer(r"(?<![\w$])" + hook + r"\(", text):
            close = balanced(text, match.end() - 1, "(", ")")
            out.append((rel, collapse(text[match.end():close])))
    return out


def literal_size(params: str | None) -> int | None:
    if not params:
        return None
    found = re.search(r"(?<![\w$])size:\s*(\d+)", params)
    return int(found.group(1)) if found else None


def offers_no_size(arg: str) -> bool:
    """Would this call site leave the hook's own `size` literal standing?

    No arguments certainly do. Otherwise the site has to name the window to shadow it -- and the one
    site that names a variable rather than a literal (`filters`) is covered by case 5, which proves
    that object always holds a number under `size`, and by case 4, which proves the spread reads it.
    """
    return arg == "" or re.search(r"(?<![\w$])size\b", arg) is None


def wire_sizes() -> dict[str, int | None]:
    """hook -> the window its own params literal offers, read off the shipped hook text.

    Every downstream claim spends this rather than the WIRE table above: an arm that deletes a
    literal has to move the verdicts, not just the table it is compared against.
    """
    return {hook: literal_size(params) for hook, (_, params) in list_wires().items()}


def test_the_ten_list_hooks_and_their_wire_literals_are_this_table():
    """Case 1: the population and its numbers, derived from the hooks' bodies rather than from here."""
    derived = list_wires()
    assert derived == WIRE, f"a hook's request window changed shape: {derived}"
    assert len(derived) == 10, f"{sorted(derived)}"
    keys = sorted(key for key, _ in derived.values())
    assert len(keys) == len(set(keys)) == 10, f"two hooks spend the same endpoint key: {keys}"


def test_every_number_a_hook_offers_is_inside_the_ceiling_the_server_enforces():
    """Case 2: eight of the ten offer a `size`, and no client asks for a window the clamp would refuse."""
    sizes = wire_sizes()
    assert sizes == {**SIZE_LITERAL, "useSavedJobs": None, "useActivityRuns": None}, sizes
    asked = sorted(n for n in sizes.values() if n is not None)
    assert len(asked) == 8, f"{sizes}"
    outside = [n for n in asked if not 1 <= n <= MAX_PAGE_SIZE]
    assert outside == [], f"a hook asks for a window Paging would clamp: {outside}"
    paging = java(PAGING)
    declared = re.search(r"MAX_PAGE_SIZE = (\d+)", paging)
    assert declared and int(declared.group(1)) == MAX_PAGE_SIZE, \
        f"the ceiling this range is measured against is {declared and declared.group(1)}"
    assert "Math.min(Math.max(size, 1), MAX_PAGE_SIZE)" in collapse(paging[paging.index("public static Window of"):]), \
        "Paging.of no longer clamps both ends, so this range claims nothing about it"


def test_the_two_literals_every_caller_shadows_and_none_without_a_caller():
    """Case 3: the call-site census, and the verdict it yields for each literal."""
    derived = {hook: call_sites(hook) for hook in WIRE}
    assert derived == SITES, f"the call sites moved: {derived}"
    # The exclusion of test files currently excludes nothing: no `*.test.ts*` names these hooks, so the
    # population below is the whole app rather than a subset chosen to make the table fit.
    with_tests = {hook: call_sites(hook, include_tests=True) for hook in WIRE}
    assert with_tests == SITES, f"a test file now spells a call site: {with_tests}"

    shipped = wire_sizes()
    unregistered = sorted(h for h in shipped if h not in SITES)
    assert not unregistered, \
        f"a list hook shipped without being registered here: {unregistered}"
    with_size = sorted(h for h, value in shipped.items() if value is not None)
    shadowed = sorted(hook for hook in with_size
                      if derived[hook] and not any(offers_no_size(arg) for _, arg in derived[hook]))
    assert shadowed == ["useApplications", "useJobs"], \
        f"these literals are shadowed by every caller: {shadowed}"
    # Empty since the notes panel: every size literal has a caller now, and the notes hook's one
    # caller passes no arguments, so its own 50 stands and reaches the wire.
    uncalled = sorted(hook for hook in with_size if derived[hook] == [])
    assert uncalled == [], \
        f"these hooks have no caller at all, so their window is never spent: {uncalled}"


def test_the_spread_that_shadows_the_jobs_20_carries_the_callers_size_unchanged():
    """Case 4: `serializeJobFilters` renames three keys and drops three value kinds; `size` is neither."""
    body = function_body(read(NORMALIZE),
                         "export function serializeJobFilters(params: object): Record<string, unknown> {")
    renamed = sorted(set(re.findall(r'k === "(\w+)"', body)))
    assert renamed == ["max_salary", "min_salary", "remote"], \
        f"the rename set grew, so a key this file calls a pass-through may now be rewritten: {renamed}"
    dropped = re.search(r"if \(v === (.*?)\) continue;", collapse(body))
    assert dropped, f"the drop clause is no longer a value comparison: {collapse(body)[:160]}"
    assert [part.strip().lstrip("v === ") for part in dropped.group(1).split("||")] == \
        ['""', "undefined", "false"], f"the drop set is {dropped.group(1)}"
    # Nothing else in the function can lose a number: it never inspects a value's type, and every
    # non-dropped, non-renamed key leaves through one `out[k] = v`.
    assert re.search(r"typeof v|Number\.|isNaN|filter\(|slice\(", body) is None, \
        "serializeJobFilters now inspects values, so a caller's size could be dropped by a rule " \
        "this file has not read"
    assert body.count("= v") == 4, f"the pass-through is no longer one clause: {body.count('= v')}"


def test_the_jobs_screen_hands_that_spread_a_number_on_every_path():
    """Case 5: `filters.size` is 12 or an address-bar integer -- never absent, so the 20 is unreachable."""
    page = read(JOBS_PAGE)
    declared_at = page.index("const DEFAULTS: FilterState = ")
    brace = page.index("{", declared_at)
    defaults = collapse(page[brace:balanced(page, brace, "{", "}") + 1])
    assert defaults == collapse("""{ q: "", skills: "", location: "", company: "", sort: "",
        page: 0, size: 12, }"""), f"the board's own defaults moved: {defaults}"
    at_shape = page.index("type FilterState = {")
    shape = page[at_shape:balanced(page, page.index("{", at_shape), "{", "}") + 1]
    fields = [collapse(line) for line in shape.splitlines()
              if re.match(r"\s+\w+\??: ", line)]
    sizes = [f for f in fields if re.match(r"size\??:", f)]
    assert sizes == ["size: number;"], \
        f"FilterState declares {sizes} of {len(fields)} fields, so a caller could hand useJobs an " \
        "object with no size and let the hook's own literal stand"

    opts = collapse(page[page.index("numericKeys"):page.index("]", page.index("numericKeys")) + 1])
    assert opts == 'numericKeys: ["page", "min_salary", "max_salary", "size"]', opts

    state = read(URL_STATE)
    hydrate = function_body(state, "export function hydrateState<")
    assert "const next = { ...initial }" in collapse(hydrate), \
        "hydrateState no longer seeds from the defaults, so a URL without ?size= can leave it absent"
    guard = re.search(r"if \(numeric\.has\(key\)\) \{ (.*?) \} else if", collapse(hydrate))
    assert guard and collapse(guard.group(1)) == "const n = asUrlNumber(raw); if (n !== undefined) next[key] = n;", \
        f"the numeric branch now writes something other than a parsed integer: {guard and guard.group(1)}"
    as_number = function_body(state, "function asUrlNumber(")
    assert collapse(as_number) == collapse("""function asUrlNumber(raw: string): number | undefined {
        const trimmed = raw.trim(); if (!trimmed) return undefined; const n = Number(trimmed);
        return Number.isInteger(n) ? n : undefined; }"""), f"asUrlNumber grew a path: {collapse(as_number)}"


def test_the_number_the_server_would_use_if_the_app_sent_none():
    """Case 6: every route's own `size` default, against the literal the hook offers for it."""
    defaults = {}
    for key in sorted(set(k for k, _ in WIRE.values())):
        ints = bound_ints(endpoint_path(key))
        defaults[endpoint_path(key)] = ints.get("size")
    assert defaults == SERVER_SIZE, f"the server side of the window moved: {defaults}"

    shipped = wire_sizes()
    unregistered = sorted(h for h in shipped if h not in WIRE)
    assert not unregistered, \
        f"a list hook shipped without a row in WIRE, so its route is unregistered here: {unregistered}"
    agrees = sorted(hook for hook, value in shipped.items()
                    if value is not None and SERVER_SIZE[endpoint_path(WIRE[hook][0])] == str(value))
    assert agrees == ["useApplications", "useCompanies", "useJobs", "useResumes"], \
        f"these literals still match their route's default: {agrees}"
    overstated = sorted(shipped[h] for h in
                        ("useKnowledgeSources", "useKnowledgeNotes", "useInterviewSessions",
                         "useConversations"))
    assert overstated == [50, 50, 50, 50] and \
        all(SERVER_SIZE[endpoint_path(k)] == "20" for k in
            ("knowledge", "knowledgeNotes", "interviews", "conversations")), \
        "four hooks no longer ask 50 where the handler says 20"


def test_the_applications_board_asks_for_exactly_the_ceiling_and_has_no_way_to_page():
    """Case 7: 100 is the whole answer, and paging it is not a thing this screen can do."""
    (site, args), = call_sites("useApplications")
    assert args == "{ size: 100 }" and site == "app/(app)/applications/page.tsx"
    assert int(re.search(r"\d+", args).group(0)) == MAX_PAGE_SIZE

    renders = sorted(str(path.relative_to(FRONT)).replace("\\", "/")
                     for path in FRONT.rglob("*.tsx") if "<Pagination" in read(path))
    assert renders == ["app/(app)/jobs/page.tsx"], \
        f"a screen gained a pager, so the ceiling stops being the whole answer: {renders}"
    apps = read(APPS_PAGE)
    assert re.search(r"applications\.data\??\.(total|page)\b", apps) is None, \
        "the applications screen now reads a window name, which case 3 of #194 did not count"
    assert "applications.data?.items ?? []" in collapse(apps), collapse(apps)[:200]
    paging = read(JAVA / PAGING)
    assert "A caller wanting more pages pages." in paging, \
        "the ceiling's own comment no longer offers that advice, so this case's contradiction moved"


def test_the_one_window_the_server_still_decides_is_a_limit_the_client_leaves_out():
    """Case 8: `/activity/runs` is the route where no client number arrives, so `defaultValue` governs."""
    key, params = list_wires()["useActivityRuns"]
    assert params == "{ limit: params?.limit }" and re.search(r"\d", params) is None, params
    client = read(CLIENT)
    builds = re.findall(r"searchParams\.set\(", client)
    assert len(builds) == 1, f"{len(builds)} places build a query string, so this reads the wrong one"
    guard = re.search(r"if \(v !== undefined\) url\.searchParams\.set\(k, String\(v\)\);", client)
    assert guard, "an omitted param is no longer left out of the URL, so `limit` would arrive as text"
    ints = bound_ints(endpoint_path(key))
    assert ints == {"limit": "30"}, f"the handler binds {ints}, not a defaulted limit"
    assert "Paging.first(limit)" in collapse(java(ACTIVITY)), \
        "the route stopped spending the ceiling, so 30 is not the same kind of number as before"
    assert ("app/(app)/activity/page.tsx", "") in call_sites("useActivityRuns"), \
        "the activity screen now sends its own window, so 30 is no longer the governing number"
