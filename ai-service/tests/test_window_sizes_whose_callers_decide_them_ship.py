"""#195: the window each list screen asks for, and which of the three numbers decides it.

#194 asked what a screen does with the window the answer carries, and found `size` has zero readers.
This file asks the other side: what does the client put in the request, and is the number it put
there the one that arrives? Three numbers can decide a request window -- the literal written in the
query hook, the argument the screen passes to that hook, and the `defaultValue` on the controller's
`@RequestParam`. Only two of the three ever get spent, and the shipped text decides which per route.

Ten hooks hand `normalizePage` a request. Nine offer a `size` literal: resumes 20, jobs 20,
applications 50, companies 20, knowledge sources 20, knowledge notes 20, interviews 20,
conversations 20, activity runs 30 -- since #225 the feed's literal, replacing the
`{ limit: params?.limit }` it sent while `/activity/runs` was the one window the server still
decided. `useSavedJobs` is the only hook that sends no window at all, because its route binds none
and answers a bare list. 19.5 made the run history the eleventh: `useIngestionRuns` asks with the
same `{ size: 20, ...(params ?? {}) }` shape every board uses, replacing the `limit` the hook used
to name while `GET /ingestion/runs` was a newest-N history. 20.1 made the nightly history the
twelfth, and the first outside `resources.ts`: `useNightlyReports` lives in `monitoring.ts` beside
the health report, so the walk reads every file under `lib/hooks/` -- a census that kept the one
filename would have watched the card page while missing the hook whose window it spends. Walking
every shipped call site outside the hooks' directory finds the literal's
own value decided elsewhere per call site rather than per hook: `useJobs`'s two callers both carry a
size (the jobs board spreads its URL-backed `filters`, the dashboard passes `{ size: 3 }`), so the
`20` at `resources.ts:182` is shadowed on every path -- and the case over `useUrlState` shows the
shadowing cannot be avoided by a bad URL, because `hydrateState` seeds `{...initial}` and only
overwrites a numeric key when `asUrlNumber` yields an integer, so `filters.size` is 12 or an
address-bar integer, never absent. Since #218 every other list has joined them: applications,
companies and interviews each have one caller asking `{ page: state.page, size: PAGE_SIZE }`; the
knowledge page's two lists do the same through two different parameter shapes
(`useKnowledgeSources` takes the window third, after `live` and `documentId`; `useKnowledgeNotes`
takes `params?`); the copilot sidebar asks `{ page: pageState.cpage, size: PAGE_SIZE }` under its own
URL key, because the page already spends `?c=` on the selected conversation; and since #225 the
activity board asks `{ page: state.page, size: PAGE_SIZE }` while the dashboard preview passes
`{ size: 5 }`. `useIngestionRuns`'s one caller is the runs panel, asking
`{ page: runPage.rpage, size: PAGE_SIZE }` under its own `?rpage=`, so its literal is shadowed on
its only path too. `useResumes` is the last per-call-site case: its screen asks `PAGE_SIZE`
(restating the route's own 20), while the dashboard and jobs callers pass no arguments -- so it is
the only literal that still spends as written, on two of its three paths.

The server's side of the same table: all ten literals now agree with the route's own
`defaultValue` -- resumes 20/20, jobs 20/20, companies 20/20, applications 50/50, activity runs
30/30, and, since #228, knowledge sources 20/20, notes 20/20, interviews 20/20 and conversations
20/20, with the run history's 20/20 joining them in 19.5. #195 measured the four of them asking 50
where the handler says 20 and left which number
should win open; it is decided here, and the decision is the boring one: the literal that loses
its only shadow is a number the app would send that the server would never have chosen, and the
pager arithmetic every one of those screens now runs is written against the same 20 the route
binds. A future caller that omits `size` on these hooks gets the server's number rather than a
stale one, which is the whole of what the fix buys.

The price of a number that only ever loses is that it cannot be seen to be wrong: an unreachable
50 contradicts nothing on screen, because nothing reads it. That is why this gate keeps the
three-way table rather than a single assertion per hook -- case 6 below is now a closed invariant
(every literal is the route's own default) instead of a note about four disagreements it chose to
record and tolerate.

The reachable numbers have consequences the screens do not cover. The applications board asked for
exactly `Paging.MAX_PAGE_SIZE` (100), which `Paging`'s own comment answers with "A caller wanting
more pages pages." -- and `<Pagination>` was written in one file app-wide, the jobs page, so the
applications screen rendered no pager and read no `total`: its 101st application was simply not
there. #218 took the ceiling's own advice, and the same arithmetic has since been given to every
other list: #220 resumes, #221 interviews, #222 companies, #223 the knowledge page's two lists,
#224 the copilot sidebar, #225 the activity feed. The page-or-raise decision is made, and #228
closed the one question it left: every hook's window is now the number its own route would have
chosen. None of the page units touched the hook literals -- each is buried on its only path, which
is the same fate #218 gave the applications literal, not a deletion.

What lands is the measurement -- per hook, per call site, per route -- from one walk of each of the
three tables.
"""


import functools
import re
from pathlib import Path

TESTS = Path(__file__).resolve().parent
AI = TESTS.parent
ROOT = AI.parent

JAVA = ROOT / "backend" / "src" / "main" / "java"
FRONT = ROOT / "frontend" / "src"

# The handlers allowed to bind `limit`, each with the reason it is not a board window. A board
# answers `page`/`size` and a total; a history asks for its newest N, and the hook names the N.
# Empty since 19.5: the one newest-N history (`GET /ingestion/runs`) pages like the boards now.
NEWEST_N: dict[str, str] = {}
HOOKS = FRONT / "lib" / "hooks"
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
    "useResumes": ("resumes", "{ size: 20, ...(params ?? {}) }"),
    "useJobs": ("jobs", "{ size: 20, ...clean }"),
    "useSavedJobs": ("savedJobs", None),
    "useApplications": ("applications", "{ size: 50, ...(params ?? {}) }"),
    "useCompanies": ("companies", "{ size: 20, ...(params ?? {}) }"),
    "useKnowledgeSources": ("knowledge", "{ size: 20, documentId, ...(params ?? {}) }"),
    "useKnowledgeNotes": ("knowledgeNotes", "{ size: 20, ...(params ?? {}) }"),
    "useInterviewSessions": ("interviews", "{ size: 20, ...(params ?? {}) }"),
    "useActivityRuns": ("activityRuns", "{ size: 30, ...(params ?? {}) }"),
    "useIngestionRuns": ("ingestionRuns", "{ size: 20, ...(params ?? {}) }"),
    "useConversations": ("conversations", "{ size: 20, ...(params ?? {}) }"),
    # 20.1's nightly history is the first paging hook outside `resources.ts`: its reader lives
    # in `monitoring.ts` beside the health report, and its default is the route's own 10.
    "useNightlyReports": ("monitoringNightlyReports", "{ size: 10, ...(params ?? {}) }"),
}

# Measured call sites, one walk; case 3 re-derives them. `""` is a call with no arguments.
SITES = {
    "useResumes": [("app/(app)/dashboard/page.tsx", ""), ("app/(app)/jobs/page.tsx", ""),
                   ("app/(app)/resumes/page.tsx", "{ page: state.page, size: PAGE_SIZE }")],
    "useJobs": [("app/(app)/dashboard/page.tsx", "{ size: 3 }"),
                ("app/(app)/jobs/page.tsx",
                 'tab === "discover" ? filters : { size: filters.size, page: filters.page }')],
    "useSavedJobs": [("app/(app)/jobs/page.tsx", "")],
    "useApplications": [("app/(app)/applications/page.tsx",
                         "{ page: state.page, size: PAGE_SIZE }")],
    "useCompanies": [("app/(app)/companies/page.tsx",
                      "{ page: state.page, size: PAGE_SIZE }")],
    "useKnowledgeSources": [("app/(app)/knowledge/page.tsx",
                            "true, src, { page: state.page, size: PAGE_SIZE }")],
    "useKnowledgeNotes": [("components/knowledge/notes-panel.tsx",
                          "{ page: state.npage, size: PAGE_SIZE }")],
    "useInterviewSessions": [("app/(app)/interviews/page.tsx",
                              "{ page: state.page, size: PAGE_SIZE }")],
    "useActivityRuns": [("app/(app)/activity/page.tsx",
                         "{ page: state.page, size: PAGE_SIZE }"),
                        ("app/(app)/dashboard/page.tsx", "{ size: 5 }")],
    "useIngestionRuns": [("components/ingestion/scheduled-feeds-panel.tsx",
                          "{ page: runPage.rpage, size: PAGE_SIZE }")],
    "useConversations": [("app/(app)/copilot/page.tsx",
                         "{ page: pageState.cpage, size: PAGE_SIZE }")],
    "useNightlyReports": [("components/monitoring/nightly-history.tsx",
                           "{ page, size: PAGE_SIZE }")],
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
    "/api/v1/activity/runs": "30",
    "/api/v1/ingestion/runs": "20",
    "/api/v1/monitoring/nightly-reports": "10",
}

# The hooks whose params object spells a numeric `size`.
SIZE_LITERAL = {
    "useResumes": 20,
    "useJobs": 20,
    "useApplications": 50,
    "useCompanies": 20,
    "useKnowledgeSources": 20,
    "useKnowledgeNotes": 20,
    "useInterviewSessions": 20,
    "useConversations": 20,
    "useActivityRuns": 30,
    "useIngestionRuns": 20,
    "useNightlyReports": 10,
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
    hook whose request window is decided somewhere, which is the question this file asks. Every file
    under `lib/hooks/` is walked -- 20.1 put the first paging hook outside `resources.ts`
    (`monitoring.ts`), and a census that read one filename would have missed its window while still
    censusing the card that pages with it.
    """
    out: dict[str, tuple[str, str | None]] = {}
    for path in sorted(HOOKS.glob("*.ts")):
        if ".test." in path.name:
            continue
        for match in re.finditer(r"export function (use\w+)\(", read(path)):
            body = function_body(read(path), match.group(0))
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
    """(file, collapsed arguments) for every call of `hook(` outside the hooks' own directory."""
    out = []
    for path in sorted(FRONT.rglob("*.ts*")):
        rel = str(path.relative_to(FRONT)).replace("\\", "/")
        if rel.startswith("lib/hooks/"):
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


def test_the_twelve_list_hooks_and_their_wire_literals_are_this_table():
    """Case 1: the population and its numbers, derived from the hooks' bodies rather than from here."""
    derived = list_wires()
    assert derived == WIRE, f"a hook's request window changed shape: {derived}"
    assert len(derived) == 12, f"{sorted(derived)}"
    keys = sorted(key for key, _ in derived.values())
    assert len(keys) == len(set(keys)) == 12, f"two hooks spend the same endpoint key: {keys}"


def test_every_number_a_hook_offers_is_inside_the_ceiling_the_server_enforces():
    """Case 2: eleven of the twelve offer a `size`, and no client asks for a window the clamp would refuse."""
    sizes = wire_sizes()
    assert sizes == {**SIZE_LITERAL, "useSavedJobs": None}, sizes
    asked = sorted(n for n in sizes.values() if n is not None)
    assert len(asked) == 11, f"{sizes}"
    outside = [n for n in asked if not 1 <= n <= MAX_PAGE_SIZE]
    assert outside == [], f"a hook asks for a window Paging would clamp: {outside}"
    paging = java(PAGING)
    declared = re.search(r"MAX_PAGE_SIZE = (\d+)", paging)
    assert declared and int(declared.group(1)) == MAX_PAGE_SIZE, \
        f"the ceiling this range is measured against is {declared and declared.group(1)}"
    assert "Math.min(Math.max(size, 1), MAX_PAGE_SIZE)" in collapse(paging[paging.index("public static Window of"):]), \
        "Paging.of no longer clamps both ends, so this range claims nothing about it"


def test_the_literals_every_caller_shadows_and_none_without_a_caller():
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
    assert shadowed == ["useActivityRuns", "useApplications", "useCompanies", "useConversations",
                        "useIngestionRuns", "useInterviewSessions", "useJobs", "useKnowledgeNotes",
                        "useKnowledgeSources", "useNightlyReports"], \
        f"these literals are shadowed by every caller: {shadowed}"
    # Empty since the notes panel: every size literal has a caller now. Only `useResumes` still
    # spends its literal as written -- on the two callers (dashboard, jobs) that pass no arguments.
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
    # Since #228 this is closed rather than recorded: #195 asked which of the three numbers
    # should win and left the four overstatements standing; the answer is the route's own
    # default, so a caller that omits `size` asks for exactly what the handler would have asked.
    drifted = sorted(hook for hook, value in shipped.items()
                     if value is not None and SERVER_SIZE[endpoint_path(WIRE[hook][0])] != str(value))
    assert drifted == [], (
        f"these literals no longer match their route's own default, so the window a caller "
        f"that omits size would ask for is one the server would never have chosen: {drifted}")


def test_the_applications_board_asks_for_exactly_the_ceiling_and_pages_the_rest():
    """Case 7: 100 rows a request, and since #218 a pager that reaches the rows past the window."""
    (site, args), = call_sites("useApplications")
    assert args == "{ page: state.page, size: PAGE_SIZE }" and site == "app/(app)/applications/page.tsx"
    apps = read(APPS_PAGE)
    pinned = re.search(r"const PAGE_SIZE = (\d+);", apps)
    assert pinned and int(pinned.group(1)) == MAX_PAGE_SIZE, \
        f"the window the board asks for is {pinned and pinned.group(1)}, not the ceiling's own number"
    assert "useUrlState<{ application?: string; page: number }>(" in collapse(apps), \
        "the page index no longer lives in the URL, so a shared board link always opens page 0"
    assert re.search(r'numericKeys: \["page"\]', apps), \
        "page is no longer the URL-bound integer the board adopts back"
    assert "applications.data?.items ?? []" in collapse(apps), collapse(apps)[:200]

    renders = sorted(str(path.relative_to(FRONT)).replace("\\", "/")
                     for path in FRONT.rglob("*.tsx") if "<Pagination" in read(path))
    assert renders == ["app/(app)/activity/page.tsx", "app/(app)/applications/page.tsx",
                       "app/(app)/companies/page.tsx", "app/(app)/copilot/page.tsx",
                       "app/(app)/interviews/page.tsx", "app/(app)/jobs/page.tsx",
                       "app/(app)/knowledge/page.tsx", "app/(app)/resumes/page.tsx",
                       "components/ingestion/scheduled-feeds-panel.tsx",
                       "components/knowledge/notes-panel.tsx",
                       "components/monitoring/nightly-history.tsx"], \
        f"the pager census moved: the boards that page give the ceiling its readers: {renders}"
    assert re.search(r"\{total > PAGE_SIZE && \(", apps), \
        "the pager is no longer gated by the window it serves, so a short board would render one"
    assert re.search(r"page=\{applications\.data\?\.page \?\? state\.page\}", apps), \
        "the pager's page index is no longer the answer's -- the half of #194's asymmetry that works"
    paging = read(JAVA / PAGING)
    assert "A caller wanting more pages pages." in paging, \
        "the ceiling's own comment no longer offers that advice, so this case's contradiction moved"


def test_the_activity_feed_pages_like_every_other_list_since_225():
    """Case 8: `/activity/runs` was the last window the server decided; it binds page/size now."""
    key, params = list_wires()["useActivityRuns"]
    assert params == "{ size: 30, ...(params ?? {}) }", \
        f"the feed's hook still leaves the window to the handler: {params}"
    ints = bound_ints(endpoint_path(key))
    assert ints == {"page": "0", "size": "30"}, \
        f"the handler binds {ints}, not a defaulted page and window"
    controller = collapse(java(ACTIVITY))
    assert ("PageDTO<RunItem> listRuns" in controller
            and "Paging.of(page, size).pageable()" in controller), (
        "the route no longer answers a clamped Page envelope, so a `?size=` past the ceiling "
        "would reach the query unbounded -- or the total would vanish with the bare array")
    assert "Paging.first(" not in controller, (
        "the feed is still clamped by the one-result helper, so a window is not a window here")
    sites = call_sites("useActivityRuns")
    assert ("app/(app)/activity/page.tsx", "{ page: state.page, size: PAGE_SIZE }") in sites, \
        f"the activity screen no longer sends its own page: {sites}"
    assert ("app/(app)/dashboard/page.tsx", "{ size: 5 }") in sites, \
        f"the dashboard preview no longer names its own window: {sites}"
    # `limit` is gone from every board handler: the only board route that bound it was this one.
    # 19.2 brought the name back for `GET /ingestion/runs`, where the run history asked for its
    # newest N -- and 19.5 retired it again: the runs panel pages, so the route binds page/size
    # and the admitted newest-N list is empty. Being admitted costs a reason, and a name that no
    # handler binds any more goes stale below rather than living on as an excuse.
    limit_bindings = sorted(f.name for f in JAVA.rglob("*.java")
                            if re.search(r"@RequestParam\([^)]*\)\s+int\s+limit\b",
                                         collapse(read(f))))
    assert limit_bindings == sorted(NEWEST_N) == [], (
        f"the handlers binding `limit` are {limit_bindings}, not the admitted newest-N list "
        f"{sorted(NEWEST_N)} -- a list route is paged, or it is a history whose caller names its N")
    for name, reason in NEWEST_N.items():
        assert reason.strip(), f"{name} is admitted with an empty reason, which explains nothing"
