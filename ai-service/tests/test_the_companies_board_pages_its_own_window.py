"""#222: the companies board pages its own window -- the fifth board, the one through the shared shell.

#195 measured `useCompanies` asking `{ size: 20 }` where `GET /companies` binds `size` with
`defaultValue = "20"` -- one of the four whose literal already agreed -- but its one caller passed
no arguments, so the screen rendered the first twenty rows with no pager and no reader of `total`:
the 21st company was simply not there, and unlike the other boards this list was also searched
(`?q=`), so "the company I researched yesterday" could be missing while a narrower search would
find it. The hook arrived in this unit already carrying `params?` and the cache key
`["companies", params]` -- a previous session prepared the shape; what was missing was the board
that spends it.

The board now asks `{ page: state.page, size: PAGE_SIZE }` with `PAGE_SIZE` restating the route's
own 20, puts the page index in the URL, and runs #219's past-the-end correction over the answer's
own window in a layout effect. The pager arrives through `ModuleView`'s new opt-in `footer` slot --
the shared shell the four ModuleView screens (companies, applications, knowledge, activity) render
through -- so this file pins both ends of that prop: the companies screen passes it gated on the
window it serves, and the shell renders it under the list once rows survive the empty check. The
hunt for a pager slot is not #221's shape: applications puts its pager inside `children` because
the Kanban board owns that slot there; companies keeps `renderItem` and needs a slot of its own.

The route side pins the clamp and the forwarding, and -- since #227 -- the order the board's pages
partition by, which this unit's first draft flagged and left open: `listCompanies` used to page
`companies.findAll(pageable)` with no `OrderBy`, so two requests for the same page could answer
different rows and a company could fall between two pages. Both branches order by name now
(`findAllByOrderByNameAsc`, `findByNameContainingIgnoreCaseOrderByNameAsc`), a column the schema
declares unique, and `CompanyOrderingIT` proves the property that order buys rather than the SQL
that spells it. The flag was right that the fix belonged to the repository owner; it was wrong that
it had to wait, so the note this gate carried as an open question is now a contract.
"""

import re
from pathlib import Path

TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parent.parent

FRONT = ROOT / "frontend" / "src"
JAVA = ROOT / "backend" / "src" / "main" / "java"
RESOURCES = FRONT / "lib" / "hooks" / "resources.ts"
COMPANIES_PAGE = FRONT / "app" / "(app)" / "companies" / "page.tsx"
MODULE_VIEW = FRONT / "components" / "common" / "module-view.tsx"
CONTROLLER = "com/careeros/job/web/CompanyController.java"


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


def test_the_hook_carries_the_window_the_board_asks_with():
    """Case 1: the signature, the key, and the spread -- the shape this unit spends."""
    body = function_body(read(RESOURCES), "export function useCompanies(")
    assert re.search(r"export function useCompanies\("
                     r"params\?: \{ page\?: number; size\?: number; q\?: string \}\)", body), (
        f"the hook lost its window parameters, so the board cannot ask for a page: "
        f"{collapse(body)[:140]}")
    assert re.search(r'queryKey: \["companies", params\]', body), (
        f"the cache no longer separates pages, so page 1 would answer from page 0's entry: "
        f"{collapse(body)[:160]}")
    assert re.search(r"api\.get<unknown>\(endpoints\.companies, "
                     r"\{ size: 20, \.\.\.\(params \?\? \{\}\) \}\)", collapse(body)), (
        f"the caller's window is no longer spread over the literal, so an asked-for page "
        f"would never reach the wire: {collapse(body)}")
    assert hook_calls("useCompanies") == [
        ("app/(app)/companies/page.tsx", "{ page: state.page, size: PAGE_SIZE }"),
    ], f"the call sites moved: {hook_calls('useCompanies')}"


def test_the_board_puts_its_page_in_the_url_and_asks_for_it():
    """Case 2: URL state, the request, and the correction -- all page-side."""
    page = read(COMPANIES_PAGE)
    pinned = re.search(r"const PAGE_SIZE = (\d+);", page)
    assert pinned and int(pinned.group(1)) == 20, (
        f"the window the board asks for is {pinned and pinned.group(1)}, not the route's own "
        "default this case measures it against")
    assert re.search(r"const PAGE_DEFAULTS: \{ page: number \} = \{ page: 0 \};", page), (
        "the defaults object is no longer the module-level const `setUrl` needs to stay stable")
    assert re.search(r"const \[state, setUrl\] = useUrlState<\{ page: number \}>\(\n"
                     r"\s*PAGE_DEFAULTS,\n"
                     r"\s*\{ numericKeys: \[\"page\"\] \}\n"
                     r"\s*\);", page), (
        "the page index no longer lives in the URL, so a shared list link always opens page 0")
    assert re.search(r"const companies = useCompanies\(\{ page: state\.page, size: PAGE_SIZE \}\);",
                     page), (
        "the screen no longer asks for the URL's page, so the pager's numbers would govern nothing")
    assert re.search(r"const total = companies\.data\?\.total \?\? 0;", page), (
        "the formula's numerator is no longer the answer's total")
    assert re.search(
        r"const lastPage = companies\.data\n"
        r"\s*\? Math\.max\(0, Math\.ceil\(total / Math\.max\(1, companies\.data\.size\)\) - 1\)\n"
        r"\s*: 0;", page), (
        "the board no longer derives lastPage from the answer's own window and total, so a "
        "shared past-the-end page would stay empty")
    assert re.search(
        r"React\.useLayoutEffect\(\(\) => \{\n"
        r"\s*if \(companies\.data && state\.page > lastPage\) setUrl\(\{ page: lastPage \}\);\n"
        r"\s*\}, \[companies\.data, state\.page, lastPage, setUrl\]\);", page), (
        "no layout effect corrects a past-the-end URL page from the answer, so the stale "
        "empty copy can paint before the correction runs")


def test_the_pager_arrives_through_the_shared_shells_footer_slot():
    """Case 3: both ends of `ModuleView`'s new opt-in footer -- the pager is gated either way."""
    page = read(COMPANIES_PAGE)
    at = page.index("<Pagination")
    block = page[at:page.index("/>", at)]
    assert re.search(r"page=\{companies\.data\?\.page \?\? state\.page\}", block), (
        "the pager's page index is no longer the answer's -- the half of #194's asymmetry that works")
    assert re.search(r"size=\{PAGE_SIZE\}", block), (
        "the pager no longer takes the window the board asks with, so its label and the "
        "request's window could drift apart")
    assert "data?.size" not in block and "data.size" not in block, (
        f"the pager now reads the answer's window: {collapse(block)}")
    assert re.search(r"total=\{total\}", block), (
        "the pager's row count no longer comes off the envelope")
    assert re.search(r'label="companies"', block), \
        "the pager no longer names the rows it pages"
    assert re.search(r"setUrl\(\{ page \}\);", block) and "window.scrollTo" in block, (
        "the pager's onPageChange no longer writes the URL page, or no longer scrolls the "
        "fresh page in")
    # The gating lives at the caller (the window it serves is the caller's number), and the shell
    # renders the prop verbatim -- so a short board renders nothing extra.
    assert re.search(r"footer=\{\s*total > PAGE_SIZE && \(", page), (
        "the pager is no longer gated by the window it serves, so a short board would render one")
    shell = read(MODULE_VIEW)
    assert re.search(r"footer\?: React\.ReactNode;", shell), (
        "the shared shell no longer declares the opt-in footer prop, so the pager would be dropped")
    assert re.search(r"\{footer\}", shell), (
        "the shell declares the footer but never renders it, so the pager would never appear")
    assert re.search(r"\{children \?\? query\.data\.items\.map\(\(item\) => renderItem\?\.\(item\)\)\}\n"
                     r"\s*\{footer\}", shell), (
        "the footer no longer sits directly under the list, so it would render above the rows")


def test_the_route_forwards_the_window_and_the_pager_restates_its_default():
    """Case 4: the defaults `PAGE_SIZE` restates, the clamp the request passes."""
    controller = collapse(java(CONTROLLER))
    assert '@RequestMapping("/api/v1/companies")' in controller, (
        "this case reads the controller whose prefix the screen's endpoint composes from")
    assert re.search(r'@RequestParam\(defaultValue = "0"\) int page, '
                     r'@RequestParam\(defaultValue = "20"\) int size\)', controller), (
        f"the route's own window moved, so the board's PAGE_SIZE restates a different "
        f"number: {controller[controller.index('@GetMapping'):][:220]}")
    assert 'return jobs.listCompanies(q, page, size);' in controller, (
        "the handler no longer forwards the request's own page and size to the service, so "
        "the window the board asks for would be decided elsewhere")
    # Both list branches carry the order their pages partition by (#227). Without it the board
    # would still page, but its pages would partition whatever the database felt like returning:
    # a repeat, a gap, or an unsorted page. `CompanyOrderingIT` holds the behaviour over real
    # HTTP; this holds the two method names that behaviour reads through.
    service = collapse(java("com/careeros/job/service/JobService.java"))
    assert "? companies.findAllByOrderByNameAsc(pageable)" in service, (
        f"the browse branch no longer orders by name, so page N is not the same slice twice: "
        f"{service[service.index('var result ='):][:180]}")
    assert ": companies.findByNameContainingIgnoreCaseOrderByNameAsc(q, pageable)" in service, (
        f"the searched branch no longer orders by name, so a ?q= page is not the slice it was: "
        f"{service[service.index('var result ='):][:180]}")
    repo = java("com/careeros/job/repository/CompanyRepository.java")
    assert "Page<Company> findAllByOrderByNameAsc(Pageable pageable);" in repo, (
        "the repository no longer declares the ordered browse query the service calls")
    assert ("Page<Company> findByNameContainingIgnoreCaseOrderByNameAsc(String q, Pageable pageable);"
            in repo), (
        "the repository no longer declares the ordered search query the service calls")
