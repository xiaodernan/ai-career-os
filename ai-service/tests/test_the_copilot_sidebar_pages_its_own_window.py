"""#224: the copilot sidebar pages its own window -- the eighth and last server-window list.

#195 measured `useConversations` asking `{ size: 50 }` where `GET /conversations` binds
`defaultValue = "20"`, and its one caller passing no arguments: the sidebar rendered the
first fifty chats with no pager and no reader of `total`, so the 51st conversation was
simply not there. With this unit every list in the app that receives a `PageDTO` spends a
window a screen owns -- jobs, applications, resumes, interviews, companies, knowledge
sources, knowledge notes, and now conversations -- and the last hook literal that reached
the wire as written (`useResumes`'s 20, on its two no-argument callers) is the only one
left, because every other caller now names its own window.

The sidebar is the first pager that does not live on its own screen: `ConversationList`
renders twice from one page (the desktop rail and the mobile sheet), and the page already
spends `?c=` on the selected conversation -- so the index takes its own URL key,
`?cpage=`, on the page's `useUrlState`, and the pager's numbers are handed down as props
rather than read from a second query. The pager sits under the scroll area, still inside
the sidebar, so it is visible in both surfaces. The selection contract is unchanged: the
active chat is fetched by id and stays open even when it sits on another page, which is
the applications board's deep-link behaviour in a sidebar.

Both routes bind 20/20; the hook's `50` is buried on its only path, like the literals
before it. Nothing about `?size=` policy is fixed here either.
"""

import re
from pathlib import Path

TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parent.parent

FRONT = ROOT / "frontend" / "src"
JAVA = ROOT / "backend" / "src" / "main" / "java"
RESOURCES = FRONT / "lib" / "hooks" / "resources.ts"
COPILOT_PAGE = FRONT / "app" / "(app)" / "copilot" / "page.tsx"
CONTROLLER = "com/careeros/conversation/web/ConversationController.java"


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
    """Case 1: the signature, the key, and the spread -- the usual list-hook shape."""
    body = function_body(read(RESOURCES), "export function useConversations(")
    assert re.search(r"export function useConversations\("
                     r"params\?: \{ page\?: number; size\?: number \}\)", body), (
        f"the hook lost its window parameters, so the sidebar cannot ask for a page: "
        f"{collapse(body)[:140]}")
    assert re.search(r'queryKey: \["conversations", params\]', body), (
        f"the cache no longer separates pages, so page 1 would answer from page 0's entry: "
        f"{collapse(body)[:160]}")
    assert re.search(r"api\.get<unknown>\(endpoints\.conversations, "
                     r"\{ size: 20, \.\.\.\(params \?\? \{\}\) \}\)", collapse(body)), (
        f"the caller's window is no longer spread over the literal, so an asked-for page "
        f"would never reach the wire: {collapse(body)}")
    assert hook_calls("useConversations") == [
        ("app/(app)/copilot/page.tsx", "{ page: pageState.cpage, size: PAGE_SIZE }"),
    ], f"the call sites moved: {hook_calls('useConversations')}"


def test_the_page_puts_the_sidebar_index_in_the_url_and_asks_for_it():
    """Case 2: `?cpage=` beside `?c=`, the request, and the correction."""
    page = read(COPILOT_PAGE)
    pinned = re.search(r"const PAGE_SIZE = (\d+);", page)
    assert pinned and int(pinned.group(1)) == 20, (
        f"the window the sidebar asks for is {pinned and pinned.group(1)}, not the route's "
        "own default this case measures it against")
    assert re.search(r"const \[pageState, setPageUrl\] = useUrlState<\{ cpage: number \}>\(\n"
                     r"\s*\{ cpage: 0 \},\n"
                     r"\s*\{ numericKeys: \[\"cpage\"\] \}\n"
                     r"\s*\);", page), (
        "the sidebar's page index no longer lives in the URL under its own key, so a shared "
        "link always opens page 0 -- or collides with the selected conversation's `?c=`")
    assert re.search(r"const conversations = useConversations\("
                     r"\{ page: pageState\.cpage, size: PAGE_SIZE \}\);", page), (
        "the screen no longer asks for the URL's page, so the pager's numbers would govern nothing")
    assert re.search(r"const total = conversations\.data\?\.total \?\? 0;", page), (
        "the formula's numerator is no longer the answer's total")
    assert re.search(
        r"const lastPage = conversations\.data \? lastPageOf\(total, conversations\.data\.size\) : 0;",
        page), (
        "the page no longer derives lastPage from the answer's own window and total, so a "
        "shared past-the-end page would stay empty")
    assert re.search(
        r"React\.useLayoutEffect\(\(\) => \{\n"
        r"\s*if \(conversations\.data && pageState\.cpage > lastPage\) setPageUrl\(\{ cpage: lastPage \}\);\n"
        r"\s*\}, \[conversations\.data, pageState\.cpage, lastPage, setPageUrl\]\);", page), (
        "no layout effect corrects a past-the-end URL page from the answer, so the stale "
        "empty copy can paint before the correction runs")
    # The deep-linked chat stays open while the sidebar pages: selection is by id, and the
    # page writer only ever touches `cpage`, so `?c=` survives both the pager and the correction.
    assert re.search(r"setPageUrl\(\{ cpage: page \}\);", page), (
        "the pager's onPageChange no longer writes the sidebar's own URL key, so the two "
        "lists' numbers would share one letter")
    assert re.search(r"url\.searchParams\.set\(\"c\", id\);", page), (
        "the selection writer no longer touches only `c`, so paging the list could drop the "
        "selected conversation from the URL")


def test_the_pager_rides_the_shared_list_component_in_both_surfaces():
    """Case 3: the numbers are handed down, and the component pages from its own props."""
    page = read(COPILOT_PAGE)
    assert re.search(r"page=\{conversations\.data\?\.page \?\? pageState\.cpage\} "
                     r"total=\{total\}", collapse(page)), (
        "the sidebar no longer hands the pager the answer's page index and the row count")
    at = page.index("<Pagination")
    block = page[at:page.index("/>", at)]
    assert re.search(r"size=\{PAGE_SIZE\}", block), (
        "the pager no longer takes the window the sidebar asks with, so its label and the "
        "request's window could drift apart")
    assert "data?.size" not in block and "data.size" not in block, (
        f"the pager now reads the answer's window: {collapse(block)}")
    assert re.search(r"page=\{page\}", block) and re.search(r"total=\{total\}", block), (
        f"the pager no longer spends the props its caller hands down: {collapse(block)}")
    assert re.search(r"onPageChange=\{onPageChange\}", block), (
        "the pager no longer writes through the caller's URL writer, so clicking it would "
        "change nothing")
    assert re.search(r"\{total > PAGE_SIZE && \(", page), (
        "the pager is no longer gated by the window it serves, so a short sidebar would render one")
    # The pager sits inside the shared component, after the scroll area and before the
    # dialog -- one component, rendered by `listPanel` into both surfaces (desktop rail and
    # mobile sheet), so each surface shows exactly one.
    assert page.count("<ConversationList") == 1, (
        "the list component no longer has a single definition, so the two surfaces could "
        "disagree about the pager")
    assert page.count("listPanel(") == 2, (
        "the listPanel helper is no longer defined once and spent twice, so one of the two "
        "surfaces could lose its pager")
    assert re.search(r"</ScrollArea>\s*\{total > PAGE_SIZE && \(\s*<Pagination", page), (
        "the pager no longer sits directly under the scroll area inside ConversationList, so "
        "it would render outside the sidebar")
    assert re.search(r"<Pagination[\s\S]*?/>\s*\)\}\s*<ConfirmDialog", page), (
        "the pager no longer precedes the delete dialog, so it moved above the list")


def test_the_route_binds_the_window_the_sidebar_restates_and_orders_the_rows():
    """Case 4: the defaults `PAGE_SIZE` restates, the clamp the request passes, the ordering."""
    controller = collapse(java(CONTROLLER))
    assert '@RequestMapping("/api/v1/conversations")' in controller, (
        "this case reads the controller whose prefix the sidebar's endpoint composes from")
    assert re.search(r'@RequestParam\(defaultValue = "0"\) int page, '
                     r'@RequestParam\(defaultValue = "20"\) int size\)', controller), (
        f"the route's own window moved, so the sidebar's PAGE_SIZE restates a different "
        f"number: {controller[controller.index('@GetMapping'):][:220]}")
    service = collapse(java("com/careeros/conversation/service/ConversationService.java"))
    assert "Paging.of(page, size).pageable()" in service and (
        "OrderByUpdatedAtDesc" in service or "OrderByCreatedAtDesc" in service), (
        "the list no longer comes back clamped and in a deterministic order, so pages of it "
        "would repeat or skip rows: " + service[:300])
