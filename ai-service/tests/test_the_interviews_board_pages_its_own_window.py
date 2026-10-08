"""#221: the interviews board pages its own window -- the fourth board, the second one whole.

#195 measured `useInterviewSessions` asking for `{ size: 50 }` while
`GET /interview/sessions` binds `size` with `defaultValue = "20"` -- one of the four
hooks whose literal overstates its route -- and its one caller passing no arguments at
all, so the screen rendered the first fifty rows -- the literal governed when no
caller window arrived -- with no pager and no reader of `total`: the 51st session was
simply not on the screen. #218/#219/#220 already settled the shape on
the other three boards; this file applies it to the fourth, and the difference the
fourth brings: its hook's literal (50) does not agree with its route's default (20),
so this is the case where the pager's constant *narrows* the window rather than
restating what the hook already asked.

The board now asks `{ page: state.page, size: PAGE_SIZE }` with `PAGE_SIZE` restating
the route's own 20, puts the page index in the URL, renders `<Pagination>` gated on
`total > PAGE_SIZE`, and runs #219's past-the-end correction over the answer's own
window. The hook takes `params?` and keys the cache `["interview", "sessions", params]`
so each page is its own entry; the literal 50 stays in the hook body, now shadowed on
the only path that exists -- what to do with the literal itself stays #195's open
question and is not touched here.

Nothing about `?size=` policy is fixed here either: `PAGE_SIZE` only ever restates
the number the route would have used anyway.
"""

import re
from pathlib import Path

TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parent.parent

FRONT = ROOT / "frontend" / "src"
JAVA = ROOT / "backend" / "src" / "main" / "java"
RESOURCES = FRONT / "lib" / "hooks" / "resources.ts"
INTERVIEWS_PAGE = FRONT / "app" / "(app)" / "interviews" / "page.tsx"
CONTROLLER = "com/careeros/interview/web/InterviewController.java"
SERVICE = "com/careeros/interview/service/InterviewService.java"


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
    """Case 1: the signature, the key, and the spread over the hook's own 50 literal."""
    body = function_body(read(RESOURCES), "export function useInterviewSessions(")
    assert re.search(r"export function useInterviewSessions\("
                     r"params\?: \{ page\?: number; size\?: number \}\)", body), (
        f"the hook lost its window parameters, so the board cannot ask for a page: "
        f"{collapse(body)[:140]}")
    assert re.search(r'queryKey: \["interview", "sessions", params\]', body), (
        f"the cache no longer separates pages, so page 1 would answer from page 0's entry: "
        f"{collapse(body)[:160]}")
    assert re.search(r"api\.get<unknown>\(endpoints\.interviews, "
                     r"\{ size: 50, \.\.\.\(params \?\? \{\}\) \}\)", collapse(body)), (
        f"the caller's window is no longer spread over the literal, so an asked-for page "
        f"would never reach the wire: {collapse(body)}")
    # The literal 50 overstates the route's 20 and stays in the body -- this gate pins that
    # it is shadowed, not deleted: #195's open question about the literal is not this unit's.
    assert hook_calls("useInterviewSessions") == [
        ("app/(app)/interviews/page.tsx", "{ page: state.page, size: PAGE_SIZE }"),
    ], f"the call sites moved: {hook_calls('useInterviewSessions')}"


def test_the_board_puts_its_page_in_the_url_and_renders_the_pager_the_rows_earn():
    """Case 2: URL state, the request, and a `<Pagination>` gated on the window it serves."""
    page = read(INTERVIEWS_PAGE)
    pinned = re.search(r"const PAGE_SIZE = (\d+);", page)
    assert pinned and int(pinned.group(1)) == 20, (
        f"the window the board asks for is {pinned and pinned.group(1)}, not the route's own "
        "default this case measures it against")
    assert "import { Pagination } from \"@/components/common/pagination\";" in page, (
        "the shared pager is no longer imported, so the rows past the first window stay unreachable")
    assert re.search(r"const PAGE_DEFAULTS: \{ page: number \} = \{ page: 0 \};", page), (
        "the defaults object is no longer the module-level const `setUrl` needs to stay stable")
    assert re.search(r"const \[state, setUrl\] = useUrlState<\{ page: number \}>\(\n"
                     r"\s*PAGE_DEFAULTS,\n"
                     r"\s*\{ numericKeys: \[\"page\"\] \}\n"
                     r"\s*\);", page), (
        "the page index no longer lives in the URL, so a shared board link always opens page 0")
    assert re.search(r"const sessions = useInterviewSessions\("
                     r"\{ page: state\.page, size: PAGE_SIZE \}\);", page), (
        "the screen no longer asks for the URL's page, so the pager's numbers would govern nothing")

    at = page.index("<Pagination")
    block = page[at:page.index("/>", at)]
    assert re.search(r"page=\{sessions\.data\?\.page \?\? state\.page\}", block), (
        "the pager's page index is no longer the answer's -- the half of #194's asymmetry that works")
    assert re.search(r"size=\{PAGE_SIZE\}", block), (
        "the pager no longer takes the window the board asks with, so its label and the "
        "request's window could drift apart")
    assert "data?.size" not in block and "data.size" not in block, (
        f"the pager now reads the answer's window: {collapse(block)}")
    assert re.search(r"total=\{total\}", block), (
        "the pager's row count no longer comes off the envelope")
    assert re.search(r'label="interview sessions"', block), \
        "the pager no longer names the rows it pages"
    assert re.search(r"\{total > PAGE_SIZE && \(", page), (
        "the pager is no longer gated by the window it serves, so a short board would render one")
    assert re.search(r"setUrl\(\{ page \}\);", block) and "window.scrollTo" in block, (
        "the pager's onPageChange no longer writes the URL page, or no longer scrolls the "
        "fresh page in")


def test_the_board_corrects_a_past_the_end_page_from_the_answers_own_window():
    """Case 3: #219's correction, over this board's own answer."""
    page = read(INTERVIEWS_PAGE)
    assert re.search(r"const total = sessions\.data\?\.total \?\? 0;", page), (
        "the formula's numerator is no longer the answer's total")
    assert re.search(
        r"const lastPage = sessions\.data\n"
        r"\s*\? Math\.max\(0, Math\.ceil\(total / Math\.max\(1, sessions\.data\.size\)\) - 1\)\n"
        r"\s*: 0;", page), (
        "the board no longer derives lastPage from the answer's own window and total, so a "
        "shared past-the-end page would stay empty")
    assert re.search(
        r"React\.useLayoutEffect\(\(\) => \{\n"
        r"\s*if \(sessions\.data && state\.page > lastPage\) setUrl\(\{ page: lastPage \}\);\n"
        r"\s*\}, \[sessions\.data, state\.page, lastPage, setUrl\]\);", page), (
        "no layout effect corrects a past-the-end URL page from the answer, so the stale "
        "empty copy can paint before the correction runs")


def test_the_route_binds_the_page_the_board_sends_and_orders_the_rows_it_pages():
    """Case 4: the defaults `PAGE_SIZE` restates, the clamp the request passes, the ordering."""
    controller = collapse(java(CONTROLLER))
    assert '@RequestMapping("/api/v1/interview/sessions")' in controller, (
        "this case reads the controller whose prefix the screen's endpoint composes from")
    assert re.search(r'@RequestParam\(defaultValue = "0"\) int page, '
                     r'@RequestParam\(defaultValue = "20"\) int size\)', controller), (
        f"the route's own window moved, so the board's PAGE_SIZE restates a different "
        f"number: {controller[controller.index('@GetMapping'):][:220]}")
    assert "return interviews.list(user.id(), page, size);" in controller, (
        "the handler no longer forwards the request's own page and size to the service, so "
        "the window the board asks for would be decided elsewhere")
    service = collapse(java(SERVICE))
    assert ("findByUserIdOrderByStartedAtDesc(userId, Paging.of(page, size).pageable())"
            in service), (
        "the list no longer comes back clamped and in a deterministic order, so pages of it "
        "would repeat or skip rows -- or a `?size=` past the ceiling would reach the query "
        "unbounded")
