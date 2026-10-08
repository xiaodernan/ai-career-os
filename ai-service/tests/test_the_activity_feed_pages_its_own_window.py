"""#225: the activity feed pages its own window -- the ninth list, and the last bare one.

#195 measured `useActivityRuns` sending `{ limit: params?.limit }` to a route that binds no
`page` at all: `/activity/runs` was the one window in the app the server still decided, because
the handler answered a bare `List<RunItem>` clamped through `Paging.first(limit)`, and the whole
`{items,total,page,size}` envelope was invented client-side by `normalizePage`'s array branch --
`total` was the length of the page in hand, so a pager over it could not have existed even in
principle. The 31st run was not there, and nothing on the screen could have known.

This unit retires that exception rather than working around it: the repository's `findRecent`
becomes a `Page` (with an explicit `countQuery`, since the JPQL carries an `:agent` filter Spring
cannot count on its own), the handler answers `PageDTO<RunItem>` over `page`/`size` like every
other list route in the app, and the activity screen gets the arithmetic every other board got --
`?page=` in the URL, `PAGE_SIZE` restating the route's own 30, `<Pagination>` through ModuleView's
footer slot, and #219's past-the-end correction over the answer's own window. The dashboard's
five-run preview sends `{ size: 5 }`, the shape the jobs preview already used.

`limit` is gone from every handler in the backend: this route was its only binder. The bare-array
branch of `normalizePage` survives on `GET /jobs/saved`, which is the case it was always gated
for. The API doc row and the golden journey move to the envelope in the same unit -- a wire change
that only half a stack made is the kind that 404s in e2e.
"""

import re
from pathlib import Path

TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parent.parent

FRONT = ROOT / "frontend" / "src"
JAVA = ROOT / "backend" / "src" / "main" / "java"
RESOURCES = FRONT / "lib" / "hooks" / "resources.ts"
ACTIVITY_PAGE = FRONT / "app" / "(app)" / "activity" / "page.tsx"
DASHBOARD_PAGE = FRONT / "app" / "(app)" / "dashboard" / "page.tsx"
MODULE_VIEW = FRONT / "components" / "common" / "module-view.tsx"
CONTROLLER = "com/careeros/activity/web/ActivityController.java"
REPOSITORY = "com/careeros/activity/repository/AgentRunRepository.java"


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


def function_body(text: str, declaration: str) -> str:
    at = text.index(declaration)
    params_end = balanced(text, text.index("(", at), "(", ")") + 1
    brace = text.index("{", params_end)
    return text[at:balanced(text, brace, "{", "}") + 1]


def hook_calls(hook: str) -> list[tuple[str, str]]:
    """(file, collapsed arguments) for every `hook(` in the shipped app outside its own file."""
    out = []
    for path in sorted(FRONT.rglob("*.ts*")):
        rel = str(path.relative_to(FRONT)).replace("\\", "/")
        if rel == "lib/hooks/resources.ts" or ".test." in rel:
            continue
        text = read(path)
        for match in re.finditer(r"(?<![\w$])" + hook + r"\(", text):
            close = balanced(text, match.end() - 1, "(", ")")
            out.append((rel, collapse(text[match.end():close])))
    return out


def test_the_hook_takes_a_window_and_keys_each_page_as_its_own_cache_entry():
    """Case 1: the signature, the key, the spread, and the two call sites' own windows."""
    body = function_body(read(RESOURCES), "export function useActivityRuns(")
    assert re.search(r"export function useActivityRuns\("
                     r"params\?: \{ page\?: number; size\?: number \}\)", body), (
        f"the hook lost its window parameters, so the feed cannot ask for a page: "
        f"{collapse(body)[:140]}")
    assert re.search(r'queryKey: \["activity", "runs", params\]', body), (
        f"the cache no longer separates pages, so page 1 would answer from page 0's entry: "
        f"{collapse(body)[:160]}")
    assert re.search(r"api\.get<unknown>\(endpoints\.activityRuns, "
                     r"\{ size: 30, \.\.\.\(params \?\? \{\}\) \}\)", collapse(body)), (
        f"the caller's window is no longer spread over the literal, so an asked-for page "
        f"would never reach the wire: {collapse(body)}")
    assert sorted(hook_calls("useActivityRuns")) == sorted([
        ("app/(app)/activity/page.tsx", "{ page: state.page, size: PAGE_SIZE }"),
        ("app/(app)/dashboard/page.tsx", "{ size: 5 }"),
    ]), f"the call sites moved: {hook_calls('useActivityRuns')}"


def test_the_feed_screen_puts_its_page_in_the_url_and_renders_the_pager_the_rows_earn():
    """Case 2: URL state, the request, the correction, the footer pager."""
    page = read(ACTIVITY_PAGE)
    pinned = re.search(r"const PAGE_SIZE = (\d+);", page)
    assert pinned and int(pinned.group(1)) == 30, (
        f"the window the feed asks for is {pinned and pinned.group(1)}, not the route's own "
        "default this case measures it against")
    assert re.search(r"const PAGE_DEFAULTS: \{ page: number \} = \{ page: 0 \};", page), (
        "the defaults object is no longer the module-level const `setUrl` needs to stay stable")
    assert re.search(r"const \[state, setUrl\] = useUrlState<\{ page: number \}>\(\n"
                     r"\s*PAGE_DEFAULTS,\n"
                     r"\s*\{ numericKeys: \[\"page\"\] \}\n"
                     r"\s*\);", page), (
        "the page index no longer lives in the URL, so a shared feed link always opens page 0")
    assert re.search(r"const runs = useActivityRuns\(\{ page: state\.page, size: PAGE_SIZE \}\);",
                     page), (
        "the screen no longer asks for the URL's page, so the pager's numbers would govern nothing")
    assert re.search(r"const total = runs\.data\?\.total \?\? 0;", page), (
        "the formula's numerator is no longer the answer's total")
    assert re.search(
        r"const lastPage = runs\.data \? lastPageOf\(total, runs\.data\.size\) : 0;",
        page), (
        "the screen no longer derives lastPage from the answer's own window and total, so a "
        "shared past-the-end page would stay empty")
    assert re.search(
        r"React\.useLayoutEffect\(\(\) => \{\n"
        r"\s*if \(runs\.data && state\.page > lastPage\) setUrl\(\{ page: lastPage \}\);\n"
        r"\s*\}, \[runs\.data, state\.page, lastPage, setUrl\]\);", page), (
        "no layout effect corrects a past-the-end URL page from the answer, so the stale "
        "empty copy can paint before the correction runs")
    at = page.index("<Pagination")
    block = page[at:page.index("/>", at)]
    assert re.search(r"page=\{runs\.data\?\.page \?\? state\.page\}", block), (
        "the pager's page index is no longer the answer's")
    assert re.search(r"size=\{PAGE_SIZE\}", block) and "data?.size" not in block \
        and "data.size" not in block, (
        f"the pager no longer takes the window the feed asks with: {collapse(block)}")
    assert re.search(r"total=\{total\}", block) and re.search(r'label="runs"', block), (
        "the pager's row count or label moved off the envelope")
    assert re.search(r"footer=\{\s*total > PAGE_SIZE && \(", page), (
        "the pager is no longer gated by the window it serves, so a short feed would render one")
    assert "{footer}" in read(MODULE_VIEW), (
        "the shared shell no longer renders the footer slot the pager arrives through")


def test_the_route_answers_a_real_envelope_and_no_handler_binds_limit_anymore():
    """Case 3: the repository, the handler, and the retirement of `limit` repo-wide."""
    repo = collapse(java(REPOSITORY))
    assert "Page<AgentRun> findRecent(" in repo, (
        f"the repository no longer answers a Page, so there is no total to page over: {repo[:200]}")
    assert 'countQuery = "SELECT COUNT(r) FROM AgentRun r' in repo, (
        "the count query is gone, so the `:agent` filter would make Spring's derived count wrong")
    controller = collapse(java(CONTROLLER))
    assert re.search(r'@RequestParam\(defaultValue = "0"\) int page, '
                     r'@RequestParam\(defaultValue = "30"\) int size, '
                     r'@RequestParam\(required = false\) String agent', controller), (
        f"the route's own window moved, so the screen's PAGE_SIZE restates a different "
        f"number: {controller[controller.index('@GetMapping'):][:260]}")
    assert ("PageDTO<RunItem> listRuns" in controller
            and "PageDTO.from(runs.findRecent(user.id(), agent, "
                "Paging.of(page, size).pageable()), ActivityController::toItem)" in controller), (
        "the handler no longer answers a clamped Page envelope built from the request's own "
        "window and the repository's total")
    assert "Paging.first(" not in controller, (
        "the route still spends the one-result helper, so a window is not a window here")
    limit_bindings = sorted(f.name for f in sorted(JAVA.rglob("*.java"))
                            if re.search(r"@RequestParam\([^)]*\)\s+int\s+limit\b",
                                         collapse(read(f))))
    assert limit_bindings == [], (
        f"a handler still binds the retired parameter, so the doc/test contract would drift: "
        f"{limit_bindings}")
