"""#220: the resumes list pages its own window -- the third board, the first one whole from the start.

`GET /api/v1/resumes` binds `page` (0) and `size` (20) and orders
`findByUserIdOrderByCreatedAtDesc`, but the app only ever asked for page 0 of the default
window: `useResumes()` took no parameters, hardcoded `{ size: 20 }`, and the resume screen
rendered the first twenty rows with no total and no pager -- the 21st resume simply was not
there. The applications board met the same truncation in #218 (there its `size` ceiling hid
the 101st) and got both halves in one unit: the request carries the page (its gate), and a
past-the-end page corrects itself (#219's gate). This file pins the third board to the same
shape from the start, so the two halves cannot arrive separately:

* the hook takes `params?: { page?: number; size?: number }`, keys the cache
  `["resumes", params]` so each page is its own entry, and spreads the caller's window over
  the literal 20 -- so the two no-argument callers (dashboard, jobs) keep page 0 of the
  default window, which is the behavior they already had;
* the screen puts the page index in the URL (`useUrlState`, numeric `page`), asks for
  `{ page: state.page, size: PAGE_SIZE }` where `PAGE_SIZE` restates the route's own
  default, and renders `<Pagination>` gated on `total > PAGE_SIZE` exactly like the other
  two boards -- the pager only exists when there is a page it can reach;
* the correction is #219's, with the answer's own window as the divisor floored at 1: a
  shared `?page=99` over two pages of resumes is rewritten to the last page that exists
  before the empty window can paint.

The route case is the other end: the defaults this screen's `PAGE_SIZE` agrees with, the
clamp the request passes through, and the ordering that makes pages of this list partition
rather than repeat rows.

Nothing about `?size=` policy is fixed here (#194/#195 own that decision): `PAGE_SIZE` only
ever restates the number the route would have used anyway.
"""

import re
from pathlib import Path

TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parent.parent

FRONT = ROOT / "frontend" / "src"
JAVA = ROOT / "backend" / "src" / "main" / "java"
RESOURCES = FRONT / "lib" / "hooks" / "resources.ts"
RESUMES_PAGE = FRONT / "app" / "(app)" / "resumes" / "page.tsx"
CONTROLLER = "com/careeros/resume/web/ResumeController.java"
SERVICE = "com/careeros/resume/service/ResumeService.java"


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
    """Case 1: the signature, the key, and the wire literal, all off the hook's own body."""
    body = function_body(read(RESOURCES), "export function useResumes(")
    assert re.search(r"export function useResumes\(params\?: \{ page\?: number; size\?: number \}\)",
                     body), (
        f"the hook lost its window parameters, so a screen cannot ask for a page: "
        f"{collapse(body)[:140]}")
    assert re.search(r'queryKey: \["resumes", params\]', body), (
        f"the cache no longer separates pages, so page 1 would answer from page 0's entry: "
        f"{collapse(body)[:160]}")
    assert re.search(r"api\.get<unknown>\(endpoints\.resumes, \{ size: 20, \.\.\.\(params \?\? \{\}\) \}\)",
                     collapse(body)), (
        f"the caller's window is no longer spread over the literal, so an asked-for page "
        f"would never reach the wire: {collapse(body)}")
    # The two screens that never asked for a window keep page 0 of the default: with no
    # arguments the spread is empty and the literal 20 governs, exactly as before the change.
    assert hook_calls("useResumes") == [
        ("app/(app)/dashboard/page.tsx", ""),
        ("app/(app)/jobs/page.tsx", ""),
        ("app/(app)/resumes/page.tsx", "{ page: state.page, size: PAGE_SIZE }"),
    ], f"the call sites moved: {hook_calls('useResumes')}"


def test_the_screen_puts_its_page_in_the_url_and_renders_the_pager_the_rows_earn():
    """Case 2: URL state, the request, and a `<Pagination>` gated on the window it serves."""
    page = read(RESUMES_PAGE)
    pinned = re.search(r"const PAGE_SIZE = (\d+);", page)
    assert pinned and int(pinned.group(1)) == 20, (
        f"the window the screen asks for is {pinned and pinned.group(1)}, not the route's own "
        "default this case measures it against")
    assert "import { Pagination } from \"@/components/common/pagination\";" in page, (
        "the shared pager is no longer imported, so the rows past the first window stay unreachable")
    assert re.search(r"const PAGE_DEFAULTS: \{ page: number \} = \{ page: 0 \};", page), (
        "the defaults object is no longer the module-level const `setUrl` needs to stay stable")
    assert re.search(r"const \[state, setUrl\] = useUrlState<\{ page: number \}>\(\n"
                     r"\s*PAGE_DEFAULTS,\n"
                     r"\s*\{ numericKeys: \[\"page\"\] \}\n"
                     r"\s*\);", page), (
        "the page index no longer lives in the URL, so a shared list link always opens page 0")
    assert re.search(r"const resumes = useResumes\(\{ page: state\.page, size: PAGE_SIZE \}\);", page), (
        "the screen no longer asks for the URL's page, so the pager's numbers would govern nothing")

    at = page.index("<Pagination")
    block = page[at:page.index("/>", at)]
    assert re.search(r"page=\{resumes\.data\?\.page \?\? state\.page\}", block), (
        "the pager's page index is no longer the answer's -- the half of #194's asymmetry that works")
    assert re.search(r"size=\{PAGE_SIZE\}", block), (
        "the pager no longer takes the window the screen asks with, so its label and the "
        "request's window could drift apart")
    assert "data?.size" not in block and "data.size" not in block, (
        f"the pager now reads the answer's window: {collapse(block)}")
    assert re.search(r"total=\{total\}", block), (
        "the pager's row count no longer comes off the envelope")
    # The pager's label reads from the locale table now, so the gate accepts the
    # key the page reads rather than the English copy it used to carry.
    assert re.search(r'label=(\{t\("resumes\.paginationLabel"\)\}|"resumes")', block), \
        "the pager no longer names the rows it pages"
    assert re.search(r"\{total > PAGE_SIZE && \(", page), (
        "the pager is no longer gated by the window it serves, so a short list would render one")
    assert re.search(r"setUrl\(\{ page \}\);", block) and "window.scrollTo" in block, (
        "the pager's onPageChange no longer writes the URL page, or no longer scrolls the "
        "fresh page in")


def test_the_screen_corrects_a_past_the_end_page_from_the_answers_own_window():
    """Case 3: #219's correction, over this board's own answer."""
    page = read(RESUMES_PAGE)
    assert re.search(r"const total = resumes\.data\?\.total \?\? 0;", page), (
        "the formula's numerator is no longer the answer's total")
    assert re.search(
        r"const lastPage = resumes\.data \? lastPageOf\(total, resumes\.data\.size\) : 0;",
        page), (
        "the board no longer derives lastPage from the answer's own window and total, so a "
        "shared past-the-end page would stay empty")
    assert re.search(
        r"React\.useLayoutEffect\(\(\) => \{\n"
        r"\s*if \(resumes\.data && state\.page > lastPage\) setUrl\(\{ page: lastPage \}\);\n"
        r"\s*\}, \[resumes\.data, state\.page, lastPage, setUrl\]\);", page), (
        "no layout effect corrects a past-the-end URL page from the answer, so the stale "
        "empty copy can paint before the correction runs")


def test_the_route_binds_the_page_the_screen_sends_and_orders_the_rows_it_pages():
    """Case 4: the defaults `PAGE_SIZE` restates, the clamp the request passes, the ordering."""
    controller = collapse(java(CONTROLLER))
    assert '@RequestMapping("/api/v1/resumes")' in controller, (
        "this case reads the controller whose prefix the screen's endpoint composes from")
    assert re.search(r'@RequestParam\(defaultValue = "0"\) int page, '
                     r'@RequestParam\(defaultValue = "20"\) int size\)', controller), (
        f"the route's own window moved, so the screen's PAGE_SIZE restates a different "
        f"number: {controller[controller.index('@GetMapping'):][:220]}")
    assert "Paging.of(page, size).pageable()" in controller, (
        "the handler no longer passes the request through the clamp this screen's window was "
        "measured against")
    service = collapse(java(SERVICE))
    assert "findByUserIdOrderByCreatedAtDescIdAsc(userId, pageable)" in service, (
        "the list no longer comes back in a deterministic order, so pages of it would repeat "
        "or skip rows")
