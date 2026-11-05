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
(`findAllByOrderByNameAsc` for the browse, and since 58.1 a JPQL `LOCATE` for `?q=`), on a column the
schema declares unique, and `CompanyOrderingIT` proves the property that order buys rather than the
SQL that spells it. The flag was right that the fix belonged to the repository owner; it was wrong that
it had to wait, so the note this gate carried as an open question is now a contract.

The searched branch is the one this file kept pinning by name, and 58.1 is why the name it now pins is
different: `findByNameContainingIgnoreCaseOrderByNameAsc` was Spring Data's derived containment query,
which wraps the caller's value in `%…%` with nothing between the reader's characters and SQL's
wildcards -- so `?q=%` answered the whole shared catalog and `?q=cn1 Under_S_ore` found a company named
"cn1 Under_Score". Neither answer is empty and neither is an error; the board returned 200 the way it
does today, which is why `CompanyNeedleIT` grades the matching and `SearchNeedleContractTest` grades
the spelling across every file in the backend that reads a reader's words.

58.2 is the half this file had been leaving open: the route answered `?q=` from #222 onward, and the
screen that pages that answer never offered the question. A reader who wanted the 21st company had to
page twenty at a time to find it, which is the complaint #222 was filed about, answered by the search
the same route already had. The board now asks `{ page, size, q }`, keeps the words in the URL beside
the page index -- so a reload, a back button or a pasted link redraws both the box and the rows -- and
puts the form in `ModuleView`'s `actions` slot rather than inventing a shared prop for one screen. The
two empties are separated on purpose: "nobody has researched a company yet" and "nothing here is
named what you typed" are different situations with different next moves, and the second one must not
send the reader off to research a company. That is #49's lesson about the replies inbox, applied here,
and it is why the narrowed empty counts the matches through the same `total` the pager reads: page two
of a word is the second page of the matches, not the second page of the catalog with its rows hidden.
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
        ("app/(app)/companies/page.tsx", "{ page: state.page, size: PAGE_SIZE, q: state.q }"),
    ], f"the call sites moved: {hook_calls('useCompanies')}"


def test_the_board_puts_its_page_in_the_url_and_asks_for_it():
    """Case 2: URL state, the request, and the correction -- all page-side."""
    page = read(COMPANIES_PAGE)
    pinned = re.search(r"const PAGE_SIZE = (\d+);", page)
    assert pinned and int(pinned.group(1)) == 20, (
        f"the window the board asks for is {pinned and pinned.group(1)}, not the route's own "
        "default this case measures it against")
    # The `q: undefined` in the defaults is load-bearing, not decoration: `hydrateState` walks the
    # union of the defaults' keys and the declared numeric keys, so a defaults object written as
    # `{ page: 0 }` would drop `q` on reload and on every pasted link -- the words would vanish from
    # the box while the rows under them stayed narrowed.
    assert re.search(r"const PAGE_DEFAULTS: \{ page: number; q\?: string \} = "
                     r"\{ page: 0, q: undefined \};", page), (
        "the defaults object is no longer the module-level const `setUrl` needs to stay stable, "
        "or no longer declares `q` as a key the URL may fill")
    assert re.search(r"const \[state, setUrl\] = useUrlState<\{ page: number; q\?: string \}>\(\n"
                     r"\s*PAGE_DEFAULTS,\n"
                     r"\s*\{ numericKeys: \[\"page\"\] \}\n"
                     r"\s*\);", page), (
        "the page index no longer lives in the URL, so a shared list link always opens page 0")
    assert re.search(r"const companies = useCompanies\(\{ page: state\.page, size: PAGE_SIZE, "
                     r"q: state\.q \}\);", page), (
        "the screen no longer asks for the URL's page and words, so the pager's numbers and the "
        "rows under them would govern nothing")
    assert re.search(r"const total = companies\.data\?\.total \?\? 0;", page), (
        "the formula's numerator is no longer the answer's total")
    assert re.search(
        r"const lastPage = companies\.data \? lastPageOf\(total, companies\.data\.size\) : 0;",
        page), (
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
    # The pager's label reads from the locale table now, so the gate accepts the
    # key the page reads rather than the English copy it used to carry. What
    # this holds is that the pager still *names* the rows it pages.
    assert re.search(r'label=(\{t\("companies\.paginationLabel"\)\}|"companies")', block), \
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
    # HTTP; this holds the two queries that behaviour reads through -- and since 58.1 the searched
    # one is a JPQL LOCATE rather than a derived `...Containing...`, which is a name the reader
    # types characters into. See `SearchNeedleContractTest` for the rule that keeps it that way.
    service = collapse(java("com/careeros/job/service/JobService.java"))
    assert "? companies.findAllByOrderByNameAsc(pageable)" in service, (
        f"the browse branch no longer orders by name, so page N is not the same slice twice: "
        f"{service[service.index('var result ='):][:180]}")
    assert ": companies.searchByName(needle, pageable)" in service, (
        f"the searched branch no longer asks the needle-shaped query, so a ?q= page is not the "
        f"slice it was: {service[service.index('var result ='):][:180]}")
    repo = java("com/careeros/job/repository/CompanyRepository.java")
    assert "Page<Company> findAllByOrderByNameAsc(Pageable pageable);" in repo, (
        "the repository no longer declares the ordered browse query the service calls")
    assert "LOCATE(:needle, LOWER(c.name)) > 0" in repo, (
        "the searched branch left LOCATE for a bound LIKE pattern, which reads the reader's "
        "percent sign and underscore as wildcards instead of as their characters")
    assert 'Page<Company> searchByName(@Param("needle") String needle, Pageable pageable);' in repo, (
        "the repository no longer declares the needle query the service calls")


def jsx_attr(source: str, name: str) -> str:
    """The braces of one JSX expression attribute, `name={…}`, balanced from its opening brace."""
    at = source.index(f"{name}={{") + len(name) + 1
    return source[at : balanced(source, at, "{", "}") + 1]


def test_the_board_asks_its_question_and_the_answer_says_whether_it_was_the_words():
    """Case 5 (58.2): the box writes the URL, the server narrows, and the two empties differ."""
    page = read(COMPANIES_PAGE)
    # Typing is a draft and asking is a URL write: one `setUrl` carries the words and the reset
    # page together, so a new question can never strand the reader on page 7 of the old answer's
    # matches -- and the effect below is the other half of the same rule, letting the address bar
    # (hydration, a back button, a pasted link) redraw the box rather than only the rows.
    assert re.search(r'const \[draft, setDraft\] = React\.useState\(state\.q \?\? ""\);', page), (
        "the box no longer opens with the words the URL carries, so a shared search would "
        "show narrowed rows over an empty box")
    assert re.search(r'React\.useEffect\(\(\) => setDraft\(state\.q \?\? ""\), \[state\.q\]\);',
                     page), (
        "the box no longer follows the URL, so clearing a search would leave the old words in it")
    assert re.search(r"const ask = \(value: string\) => "
                     r"setUrl\(\{ q: value\.trim\(\) \|\| undefined, page: 0 \}\);", page), (
        "asking no longer trims, or no longer resets to the first page of the new matches, or "
        "no longer leaves the URL free of an empty `q`")

    form = jsx_attr(page, "actions")
    assert re.search(r'<form\n\s*role="search"', form), (
        "the words are no longer asked as a form, so there is no default to prevent and Enter "
        "would reload the screen instead of searching it")
    assert re.search(r"onSubmit=\{\(event\) => \{\n\s*event\.preventDefault\(\);\n\s*ask\(draft\);",
                     form), (
        f"submitting the box no longer asks the server with the draft: {collapse(form)[:120]}")
    assert re.search(r'value=\{draft\}', form) and \
        re.search(r"onChange=\{\(event\) => setDraft\(event\.target\.value\)\}", form), (
        "the box is no longer the draft it will ask with, so what the reader sees and what the "
        "URL says could be different sentences")
    assert re.search(r'placeholder=\{t\("companies\.searchPlaceholder"\)\}', form) and \
        re.search(r'aria-label=\{t\("companies\.searchLabel"\)\}', form), (
        "the box no longer says what it searches, in either the visible or the announced copy")
    assert re.search(r"autoComplete=\"off\"", form), (
        "the box is offering the browser's own history again: a shared list of names this "
        "reader once typed, which is not this product's data to leak that way")
    assert re.search(r"\{state\.q \? \(", form), (
        f"the clear button is no longer gated on a search being on: {collapse(form)[:160]}")
    assert form.count("ask(\"\")") + form.count("ask('')") >= 1 and 'setDraft("")' in form, (
        "clearing no longer drops both the box's words and the URL's, so one empty question "
        "would still be on the wire")

    # The empty copy is the answer's other half: a catalog nobody researched and a catalog none of
    # which matches the words are different situations, and the second one's escape is the words,
    # not a research prompt (#49's rule for the replies inbox).
    empty = jsx_attr(page, "emptyHint")
    assert re.search(r"emptyHint=\{\s*state\.q", page), (
        "the empty state no longer branches on whether a search is on")
    assert re.search(r'title: t\("companies\.noMatch", \{ query: state\.q \}\)', empty), (
        "the narrowed empty no longer names the words that found nothing, so a reader cannot "
        "tell a typo from an empty catalog")
    assert re.search(r"action: \(", empty) and re.search(r't\("companies\.clearSearch"\)', empty), (
        "the narrowed empty offers no way back to the whole catalog")
    assert re.search(r'title: t\("companies\.noneResearched"\)', empty), (
        "the unsearched empty lost the copy that sends the reader to research a company")
    # The narrowing is the server's, so the pager's `total` and the rows agree. A client-side
    # filter over `data.items` would make both the count and page two lie.
    assert "toLowerCase()" not in page, (
        "the board now narrows its own page instead of asking the route, so the pager would "
        "count the whole catalog over a filtered slice of one window")

    # The slot the box uses is the shell's existing one: a prop this screen passes and the shell
    # already renders above the loading/empty/error branches, so the words stay editable while
    # the previous answer is still arriving.
    shell = read(MODULE_VIEW)
    assert re.search(r"actions\?: React\.ReactNode;", shell), (
        "the shared shell no longer declares the slot this screen's form goes through")
    assert re.search(r"actions=\{\s*<>\s*\{actions\}", shell), (
        "the shell no longer renders the actions slot, so the form would never appear")
