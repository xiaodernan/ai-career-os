"""#194: the four page-envelope names, bound to the screens that spend them.

#159 bound `normalizePage` to `PageDTO` and deleted a dead reader; #193 pinned that
`GET /jobs/saved` answers a bare `List<SavedJobItem>` so the array branch is the only reachable one
there. Neither asked the other direction: what does a screen actually do with the four names the
envelope carries, once the server has decided the window for itself?

Ten query hooks annotate `Promise<Page<X>>`. Two sit over a route that answers a bare list --
`GET /jobs/saved` and `GET /activity/runs` -- so their whole envelope is invented client-side; eight
get a real `PageDTO`. `PageDTO` declares `items`, `total`, `page`, `size`, and both branches of
`normalizePage` fill all four. `Paging.of` floors the page at 0 and keeps the window inside
1..`MAX_PAGE_SIZE` (100), and `JobService.list` reports that clamped `window.size()` rather than the
number it was handed -- so the answer always carries the window that was really used. Walking every
shipped file under `frontend/src` for a read of these four names off a query result finds readers for
`items`, `total` and `page`, and -- since #219/#220/#221 -- exactly four readers of `size`: the four
server-window boards (jobs, applications, resumes, interviews), each correcting a past-the-end URL
page from the answer's own window (`test_a_past_the_end_page_corrects_itself.py`,
`test_the_resumes_list_pages_its_own_window.py`,
`test_the_interviews_board_pages_its_own_window.py`). The app's four pagers are still all fed the
client's own number -- the jobs board the address-bar integer `filters.size`, the applications board
(#218) the `PAGE_SIZE` constant it asks with, the resumes list (#220) its `PAGE_SIZE` restating the
route's own 20, the interviews board (#221) its `PAGE_SIZE` restating the route's own 20 -- so the
window the answer really carried feeds the correction, not the label.
The activity screen goes further and reads nothing but `items` through `ModuleView`.

That asymmetry is what the two clamps disagree about. `asUrlNumber` adopts any integer, and its own
docstring says a negative page is passed through because "the window it reports corrects the pager"
-- true for `page`, which the pager does read, and unimplemented for `size`, which nobody does. On
the Discover tab the window is the server's (`num(raw, "page")`) and `?size=5000` asks for 5000 rows,
gets the 100 the ceiling allows, and then `total > filters.size` is false, so the pager that would
reach row 101 is never rendered. On the Saved tab the same URL number drives the client-side window:
`filterAndPaginate` refuses a non-positive size and falls back to `filtered.length || 1`, so all the
rows show, while `<Pagination>` is handed `size={0}` and prints `from = 0 * 0 + 1`, `to = min(total,
1 * 0)` -- "1-0 of 7" over a list that is showing seven. The saved hook's own comment already
concedes the wire half ("a page size here would be a number the server never reads"); this file pins
the client half, where the number is read -- just never the one that shipped.

Nothing about `?size=` policy is fixed here: the two clamps and the jobs pager that `?size=5000`
hides stay owner decisions. What lands is the measurement, per name and per file, from one walk.
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
JOBS_PAGE = FRONT / "app" / "(app)" / "jobs" / "page.tsx"
APPS_PAGE = FRONT / "app" / "(app)" / "applications" / "page.tsx"
RESUMES_PAGE = FRONT / "app" / "(app)" / "resumes" / "page.tsx"
INTERVIEWS_PAGE = FRONT / "app" / "(app)" / "interviews" / "page.tsx"
JOB_FILTER = FRONT / "lib" / "job-filter.ts"
PAGINATION = FRONT / "components" / "common" / "pagination.tsx"
URL_STATE = FRONT / "lib" / "hooks" / "use-url-state.ts"
PAGE_DTO = "com/careeros/common/PageDTO.java"
PAGING = "com/careeros/common/Paging.java"
JOB_CONTROLLER = "com/careeros/job/web/JobController.java"
JOB_SERVICE = "com/careeros/job/service/JobService.java"

API_PREFIX = "/api/v1"

# Measured off this plane, then re-derived by case 1 from the annotations themselves: hook ->
# (the endpoint key its query spends, the return type the route behind that key declares).
PAGE_HOOKS = {
    "useResumes": ("resumes", "PageDTO<ResumeListItem>"),
    "useJobs": ("jobs", "PageDTO<JobListItem>"),
    "useSavedJobs": ("savedJobs", "List<SavedJobItem>"),
    "useApplications": ("applications", "PageDTO<ApplicationItem>"),
    "useCompanies": ("companies", "PageDTO<CompanyItem>"),
    "useKnowledgeSources": ("knowledge", "PageDTO<SourceItem>"),
    "useKnowledgeNotes": ("knowledgeNotes", "PageDTO<NoteItem>"),
    "useInterviewSessions": ("interviews", "PageDTO<SessionItem>"),
    "useActivityRuns": ("activityRuns", "List<RunItem>"),
    "useConversations": ("conversations", "PageDTO<ConversationItem>"),
}

BARE_LIST_HOOKS = ["useActivityRuns", "useSavedJobs"]

ENVELOPE = ["items", "total", "page", "size"]

# Measured reader files per envelope name. The population is every `*.ts*` under frontend/src except
# `lib/api/normalize.ts` (the producer) and the `*.test.ts*` files, which quote production source as
# strings rather than reading a response.
READERS = {
    "items": ["app/(app)/applications/page.tsx", "app/(app)/copilot/page.tsx",
              "app/(app)/dashboard/page.tsx", "app/(app)/jobs/page.tsx",
              "components/common/module-view.tsx", "lib/hooks/resources.ts"],
    "total": ["app/(app)/applications/page.tsx", "app/(app)/interviews/page.tsx",
              "app/(app)/jobs/page.tsx", "app/(app)/resumes/page.tsx"],
    "page": ["app/(app)/applications/page.tsx", "app/(app)/interviews/page.tsx",
             "app/(app)/jobs/page.tsx", "app/(app)/resumes/page.tsx"],
    "size": ["app/(app)/applications/page.tsx", "app/(app)/interviews/page.tsx",
             "app/(app)/jobs/page.tsx", "app/(app)/resumes/page.tsx"],
}

MAX_PAGE_SIZE = 100
DEFAULT_SIZE = 12


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


def record_components(rel: str, name: str) -> list[str]:
    text = java(rel)
    at = text.index(f"record {name}")
    return [a.split()[-1] for a in top_level_args(text, text.index("(", at))]


def spring_gets() -> dict[str, list[tuple[str, str, str]]]:
    """Full path -> [(return type, handler, controller)] for every @GetMapping."""
    found: dict[str, list[tuple[str, str, str]]] = {}
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
            if verb == "Get":
                found.setdefault(prefix + (sub or ""), []).append(
                    (ret.strip(), handler, str(path.relative_to(JAVA)).replace("\\", "/")))
    return found


def endpoint_path(key: str) -> str:
    declared = re.search(r"^\s+" + key + r': "([^"]*)"', read(ENDPOINTS), re.M)
    assert declared, f"endpoints.ts declares no {key!r}"
    return API_PREFIX + declared.group(1)


def page_typed_hooks() -> dict[str, tuple[str, str]]:
    """hook -> (the endpoint key it spends, the return type its route declares), one walk."""
    resources = read(RESOURCES)
    out: dict[str, tuple[str, str]] = {}
    gets = spring_gets()
    for match in re.finditer(r"export function (use\w+)\(", resources):
        name = match.group(1)
        body = function_body(resources, match.group(0))
        annotated = re.findall(r"Promise<Page<(\w+)>>", body)
        if not annotated:
            continue
        assert len(annotated) == 1, f"{name} annotates {annotated}"
        keys = sorted(set(re.findall(r"endpoints\.(\w+)", body)))
        assert len(keys) == 1, f"{name} spends {keys}, not one endpoint key"
        path = endpoint_path(keys[0])
        routes = gets.get(path, [])
        assert len(routes) == 1, f"{path} answers {routes}, not one GET"
        out[name] = (keys[0], routes[0][0])
    return out


def envelope_reads() -> dict[str, list[str]]:
    """Every read of an envelope name off a query result, by name, over the shipped app code.

    One scan for all four names, so an empty list under `size` is the same scan that fills the other
    three: a receiver chain (dotted or bare) ending in `data`, optional-chained, then the name. The
    population is every `*.ts*` under frontend/src except `lib/api/normalize.ts`, which writes these
    names instead of reading them, and except test files, whose assertions quote production source
    as strings rather than spending a response. Case 4 checks the reach, not just the result.
    """
    found: dict[str, list[str]] = {name: [] for name in ENVELOPE}
    for path in sorted(FRONT.rglob("*.ts*")):
        rel = str(path.relative_to(FRONT)).replace("\\", "/")
        if rel == "lib/api/normalize.ts" or ".test." in rel:
            continue
        text = read(path)
        for name in ENVELOPE:
            if re.search(r"(?<![\w$])[\w$.]*\.?data\??\." + name + r"\b", text):
                found[name].append(rel)
    return found


def test_the_page_typed_hooks_are_ten_and_two_sit_over_a_bare_list():
    """Case 1: the population, derived from the annotations rather than from this table."""
    derived = page_typed_hooks()
    assert derived == PAGE_HOOKS, f"the page-typed hooks moved: {derived}"
    bare = sorted(name for name, (_, ret) in derived.items() if ret.startswith("List<"))
    assert bare == BARE_LIST_HOOKS, f"hooks that promise a page over a bare list: {bare}"
    paged = [ret for _, ret in derived.values() if ret.startswith("PageDTO<")]
    assert len(paged) == len(derived) - len(bare) == 8, f"{paged}"


def test_the_envelope_is_four_names_that_both_branches_and_the_record_all_agree_on():
    """Case 2: normalizePage's two branches and PageDTO declare the same four slots."""
    page = function_body(read(NORMALIZE), "export function normalizePage<T>(")
    array = re.search(r"if \(Array\.isArray\(raw\)\) \{\n\s*return \{([^}]*)\}", page)
    assert array, "normalizePage no longer short-circuits a list into the envelope"
    synthesized = [m.group(1) for m in re.finditer(r"(\w+):", array.group(1))]
    assert synthesized == ENVELOPE, f"the array branch now writes {synthesized}"
    assert re.search(r"total: raw\.length, page: 0, size: raw\.length", page), (
        "the array branch no longer claims the whole list is one first page, which is the claim "
        "the Saved tab's pager inherits")
    object_branch = page[page.index("const arr = list("):]
    read_by_helper = [m.groups() for m in re.finditer(r'\b(list|num)\(raw, "(\w+)"',
                                                     object_branch)]
    assert sorted(n for _, n in read_by_helper) == sorted(ENVELOPE), (
        f"the object branch reads {read_by_helper}")
    assert {h for h, _ in read_by_helper} == {"list", "num"}, (
        f"the object branch now goes through {sorted({h for h, _ in read_by_helper})}")
    assert record_components(PAGE_DTO, "PageDTO") == ENVELOPE, (
        "PageDTO's components and the envelope this file walks are no longer the same four names")


def test_the_window_the_server_used_is_read_only_where_a_page_corrects_itself():
    """Case 4: items, total and page have readers; size's only four are the corrections."""
    reads = envelope_reads()
    assert reads == READERS, f"the envelope reader census moved: {reads}"
    assert "app/(app)/jobs/page.tsx" in reads["items"], (
        "the scan no longer reaches the one screen with a pager, so a zero under `size` would "
        "be an unread population rather than an absent name")
    assert "components/common/module-view.tsx" in reads["items"], (
        "the scan no longer reaches the shared list renderer either")
    assert "app/(app)/applications/page.tsx" in reads["total"], (
        "the applications pager (#218) left the census, so the empty list under `size` below "
        "would be an unread population rather than an unread name")
    assert "app/(app)/resumes/page.tsx" in reads["total"], (
        "the resumes pager (#220) left the census, so a `size` read there would be invisible "
        "to the population this case measures")
    assert "app/(app)/interviews/page.tsx" in reads["total"], (
        "the interviews pager (#221) left the census, so a `size` read there would be invisible "
        "to the population this case measures")
    assert reads["size"] == ["app/(app)/applications/page.tsx", "app/(app)/interviews/page.tsx",
                             "app/(app)/jobs/page.tsx", "app/(app)/resumes/page.tsx"], (
        f"the answer's window has readers beyond the four corrections: {reads['size']}")


def test_the_four_pagers_are_fed_client_numbers_and_the_answered_window_still_is_not_one():
    """Case 5: all four `<Pagination>`s take the window the caller asked with, never the answer's."""
    consumers = sorted(str(p.relative_to(FRONT)).replace("\\", "/")
                       for p in FRONT.rglob("*.tsx")
                       if 'from "@/components/common/pagination"' in read(p))
    assert consumers == ["app/(app)/applications/page.tsx", "app/(app)/interviews/page.tsx",
                         "app/(app)/jobs/page.tsx", "app/(app)/resumes/page.tsx"], \
        f"pager consumers: {consumers}"
    jobs = read(JOBS_PAGE)
    block = jobs[jobs.index("<Pagination"):]
    block = block[:block.index("/>")]
    assert re.search(r"size=\{filters\.size\}", block), (
        "the pager no longer takes its window from the URL state, so the dead `size` above "
        "needs re-reading")
    assert "data?.size" not in block and "data.size" not in block, (
        f"the pager now reads the answer's window: {block}")
    assert re.search(r"page=\{listView\.data\?\.page \?\? filters\.page\}", block), (
        "the page index is no longer the answer's, which is the half of the asymmetry that works")
    assert re.search(r"total=\{total\}", block) and re.search(
        r"const total = listView\.data\?\.total \?\? 0;", jobs), (
        "the pager's row count no longer comes off the envelope")

    apps = read(APPS_PAGE)
    ablock = apps[apps.index("<Pagination"):]
    ablock = ablock[:ablock.index("/>")]
    assert re.search(r"size=\{PAGE_SIZE\}", ablock), (
        "the board's pager no longer takes the constant the board asks with, so its window "
        "and the request's window could drift apart")
    assert "data?.size" not in ablock and "data.size" not in ablock, (
        f"the board's pager now reads the answer's window, so the dead `size` above has a reader: {ablock}")
    assert re.search(r"page=\{applications\.data\?\.page \?\? state\.page\}", ablock), (
        "the board's page index is no longer the answer's")
    assert re.search(r"total=\{total\}", ablock) and re.search(
        r"const total = applications\.data\?\.total \?\? 0;", apps), (
        "the board's pager row count no longer comes off the envelope")

    resumes = read(RESUMES_PAGE)
    rblock = resumes[resumes.index("<Pagination"):]
    rblock = rblock[:rblock.index("/>")]
    assert re.search(r"size=\{PAGE_SIZE\}", rblock), (
        "the list's pager no longer takes the constant the list asks with, so its window "
        "and the request's window could drift apart")
    assert "data?.size" not in rblock and "data.size" not in rblock, (
        f"the list's pager now reads the answer's window, so the dead `size` above has a reader: {rblock}")
    assert re.search(r"page=\{resumes\.data\?\.page \?\? state\.page\}", rblock), (
        "the list's page index is no longer the answer's")
    assert re.search(r"total=\{total\}", rblock) and re.search(
        r"const total = resumes\.data\?\.total \?\? 0;", resumes), (
        "the list's pager row count no longer comes off the envelope")

    interviews = read(INTERVIEWS_PAGE)
    iblock = interviews[interviews.index("<Pagination"):]
    iblock = iblock[:iblock.index("/>")]
    assert re.search(r"size=\{PAGE_SIZE\}", iblock), (
        "the interviews pager no longer takes the constant the board asks with, so its window "
        "and the request's window could drift apart")
    assert "data?.size" not in iblock and "data.size" not in iblock, (
        f"the interviews pager now reads the answer's window, so the dead `size` above has a reader: {iblock}")
    assert re.search(r"page=\{sessions\.data\?\.page \?\? state\.page\}", iblock), (
        "the interviews board's page index is no longer the answer's")
    assert re.search(r"total=\{total\}", iblock) and re.search(
        r"const total = sessions\.data\?\.total \?\? 0;", interviews), (
        "the interviews pager row count no longer comes off the envelope")


def test_the_backend_reports_the_clamped_window_and_the_url_never_adopts_the_ceiling():
    """Case 6: Paging bounds the window, JobService ships the bound, the client ignores it."""
    paging = java(PAGING)
    assert re.search(r"public static final int MAX_PAGE_SIZE = (%d);" % MAX_PAGE_SIZE, paging), (
        "the window ceiling moved; this file's 5000-row scenario is measured against it")
    window = function_body(paging, "public static Window of(")
    assert re.search(r"new Window\(Math\.max\(page, 0\), Math\.min\(Math\.max\(size, 1\), "
                     r"MAX_PAGE_SIZE\)\)", window), f"Paging.of no longer clamps both: {window}"
    body = function_body(java(JOB_SERVICE), "public PageDTO<JobListItem> list(")
    of_args = top_level_args(body, body.index("(items", body.index("PageDTO.of(")))
    assert [a.strip() for a in of_args[-2:]] == ["window.page()", "window.size()"], of_args
    assert "page" not in of_args and "size" not in of_args, (
        f"the answer now reports a window other than the one it used: {of_args}")


def test_the_url_number_that_reaches_the_pager_has_no_floor_and_no_ceiling():
    """Case 7: asUrlNumber bounds integers only by being integers."""
    number = function_body(read(URL_STATE), "function asUrlNumber(")
    assert re.search(r"return Number\.isInteger\(n\) \? n : undefined;", number), (
        f"asUrlNumber now bounds the value it adopts: {number}")
    assert not re.search(r"[<>]", number), (
        "asUrlNumber has grown a comparison, so the address bar no longer reaches the pager "
        f"unbounded: {number}")
    jobs = read(JOBS_PAGE)
    assert re.search(r"numericKeys: \[[^\]]*\"size\"", jobs), "size is no longer URL-bound"
    assert re.search(r"size: %d," % DEFAULT_SIZE, jobs), "the default window moved"
    assert re.search(r"const listView = tab === \"saved\" \? \(\{ \.\.\.saved, data: savedPage \}"
                     r" as typeof saved\) : jobs;", jobs), (
        "the Saved tab no longer swaps in a client-side window, so the pager's numbers come "
        "from somewhere else now")


def test_the_two_clamps_disagree_about_size_zero_because_only_one_of_them_sees_it():
    """Case 8: filterAndPaginate refuses a non-positive window; the pager only guards it."""
    filtered = function_body(read(JOB_FILTER), "export function filterAndPaginate(")
    assert re.search(r"const size = filters\.size && filters\.size > 0 \? filters\.size : "
                     r"filtered\.length \|\| 1;", filtered), (
        f"the client window no longer falls back off a 0 size: {filtered[:200]}")
    assert re.search(r"const page = Math\.min\(Math\.max\(0, filters\.page \?\? 0\), lastPage\);",
                     filtered), "the client page index is no longer clamped"
    assert re.search(r"total: filtered\.length,\s*page,\s*size,", filtered), (
        "filterAndPaginate no longer returns its own honest window in the envelope shape, which "
        "is the number the pager is not given")
    pgn = read(PAGINATION)
    assert re.search(r"const pageCount = size > 0 \? Math\.max\(1, Math\.ceil\(total / size\)\)"
                     r" : 1;", pgn), "the pager's own zero guard moved"
    assert re.search(r"const from = total === 0 \? 0 : page \* size \+ 1;", pgn), (
        "the row-count label no longer multiplies the number it was handed")
    assert re.search(r"const to = Math\.min\(total, \(page \+ 1\) \* size\);", pgn), (
        "the label's upper bound moved")
    assert "size=0" not in pgn and "Math.max(1, size)" not in pgn, (
        "the pager has grown its own floor, which is the fix this file is not making")


def test_the_bare_list_route_binds_no_window_at_all_so_its_hook_cannot_ask_for_one():
    """Case 9: /jobs/saved takes only the caller, while /jobs binds page and size."""
    gets = spring_gets()
    saved = gets[endpoint_path("savedJobs")]
    assert len(saved) == 1 and saved[0][0].startswith("List<"), saved
    ret, handler, controller = saved[0]
    text = java(controller)
    at = text.index(f"{ret} {handler}(")
    params = top_level_args(text, text.index("(", at))
    assert [p.split()[-1] for p in params] == ["user"], (
        f"/jobs/saved now binds {[p for p in params]}")
    jobs = gets[endpoint_path("jobs")]
    assert len(jobs) == 1, jobs
    ret, handler, controller = jobs[0]
    text = java(controller)
    at = text.index(f"{ret} {handler}(")
    bound = [p for p in top_level_args(text, text.index("(", at))]
    assert sum(1 for p in bound if '"page"' in p or "page" in p.split()[-1]) == 1, bound
    assert sum(1 for p in bound if p.split()[-1] == "size") == 1, bound
    assert 'size: 20' in read(RESOURCES), (
        "useJobs asks the wire for a window again, and the number it asks with is the one "
        "the pager divides by")
