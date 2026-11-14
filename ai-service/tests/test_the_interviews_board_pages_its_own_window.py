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
restating what the hook already asked. (#228 has since moved that literal to 20, so
the narrowing is gone and the constant restates the route again.)

The board now asks `{ page: state.page, size: PAGE_SIZE }` with `PAGE_SIZE` restating
the route's own 20, puts the page index in the URL, renders `<Pagination>` gated on
`total > PAGE_SIZE`, and runs #219's past-the-end correction over the answer's own
window. The hook takes `params?` and keys the cache `["interview", "sessions", params]`
so each page is its own entry; #228 moved the hook's literal to the route's own 20, so
the literal is no longer shadowed by anything and the window the wire sees is the one
the board asked for.

Nothing about `?size=` policy is fixed here either: `PAGE_SIZE` only ever restates
the number the route would have used anyway.

70.4 gave the route a word, and the two derived reads cases 4 and 5 used to pin by name are
one `findPage(userId, applicationId, needle, pageable)` now. The claims did not move, so the
cases follow them to where they now live: the window is still the route's own two defaults,
the clamp is still `Paging.of`, and the total order and the card's second scope are read out
of the repository's one query rather than out of a method name that spelled them.

70.5 gave the route its reader, and cases 1, 2 and 5 moved with it: the hook now takes `q` and
spells it on the wire beside `applicationId`, the board's defaults object declares the word so a
pasted `/interviews?q=` link restores it, and its request carries both scopes at once. Case 7 is
new and measures the box itself -- the draft and the question are separate state, asking resets
the page, and the board now has three empties rather than two.
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
REPOSITORY = "com/careeros/interview/repository/InterviewSessionRepository.java"


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
    """Case 1: the signature, the key, and the window this hook spells name by name."""
    body = function_body(read(RESOURCES), "export function useInterviewSessions(")
    signature = collapse(body)
    # 59.1 added the fourth parameter, `enabled`: the report and the runner ask only when
    # the session names a card. It is a gate, not a window, so it is named here beside the
    # three the board uses rather than folded into them. 70.5 added `q`, which is neither:
    # it is the question the board asks its window of.
    for part in ("params?: {", "page?: number;", "size?: number;",
                 "applicationId?: string;", "q?: string;", "enabled?: boolean;"):
        assert part in signature, (
            f"the hook lost {part!r}, so the board cannot ask for a page: {signature[:160]}")
    assert re.search(r'queryKey: \["interview", "sessions", params\]', body), (
        f"the cache no longer separates pages, so page 1 would answer from page 0's entry: "
        f"{collapse(body)[:160]}")
    # `enabled` is a gate, not a window (59.1), and the other four are spelled rather than spread:
    # `...query` hides the key names from the endpoints reader that checks each one against the
    # handler's signature, and a parameter that reader stops seeing is one Spring may quietly ignore
    # -- 49.1 took the reply list off the same cliff.
    assert re.search(r"enabled: params\?\.enabled \?\? true,", body), (
        f"the gate is no longer answerable without reaching the wire: {collapse(body)[:160]}")
    assert re.search(r"api\.get<unknown>\(endpoints\.interviews, \{ size: params\?\.size \?\? 20, "
                     r"page: params\?\.page, applicationId: params\?\.applicationId, "
                     r"q: params\?\.q, \}\)",
                     collapse(body)), (
        f"the caller's window no longer reaches the wire key by key: {collapse(body)}")
    request = collapse(body).split("endpoints.interviews, ")[1].split(")")[0]
    assert request.startswith("{") and "..." not in request, (
        f"a spread joined the request object, so the endpoints gate cannot name its parameters: "
        f"{request}")
    # #228 moved the literal to the route's own 20, so the two now agree; what this gate
    # still pins is that a caller's window overrides it rather than replaces it.
    # Four callers now: the board (its own page), the report (59.1), the runner (62.1) —
    # and the closing ceremony (212), which reads the interview total for its stat tiles.
    assert hook_calls("useInterviewSessions") == [
        ("app/(app)/ceremony/page.tsx",
         "{ size: 1, page: 0 }"),
        ("app/(app)/interviews/[id]/page.tsx",
         "{ applicationId: data?.applicationId ?? undefined, size: 20, "
         "enabled: Boolean(data?.applicationId), }"),
        ("app/(app)/interviews/[id]/report/page.tsx",
         "{ applicationId: session.data?.applicationId ?? undefined, size: 20, "
         "enabled: Boolean(session.data?.applicationId), }"),
        ("app/(app)/interviews/page.tsx",
         "{ page: state.page, size: PAGE_SIZE, applicationId, q: state.q, }"),
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
    # Both optional keys are declared in the defaults, not only the word: `hydrateState` walks the
    # union of `initial`'s keys and the numeric ones, so the card filter had been silently
    # un-restorable from a pasted link since 57.1 shipped it. 70.5 found that while adding `q`, and
    # the shape is pinned here so neither key can be dropped from the defaults again.
    assert re.search(r"const PAGE_DEFAULTS: \{ page: number; application\?: string; q\?: string \} "
                     r"= \{\s*page: 0,\s*application: undefined,\s*q: undefined,\s*\};", page), (
        "the defaults object is no longer the module-level const `setUrl` needs to stay stable, "
        "or it stopped declaring a key a pasted link has to restore")
    assert re.search(r"const \[state, setUrl\] = "
                     r"useUrlState<\{ page: number; application\?: string; q\?: string \}>\(\n"
                     r"\s*PAGE_DEFAULTS,\n"
                     r"\s*\{ numericKeys: \[\"page\"\] \}\n"
                     r"\s*\);", page), (
        "the page index no longer lives in the URL, so a shared board link always opens page 0")
    assert re.search(r"const sessions = useInterviewSessions\(\{\n"
                     r"\s*page: state\.page,\n"
                     r"\s*size: PAGE_SIZE,\n"
                     r"\s*applicationId,\n"
                     r"\s*q: state\.q,\n"
                     r"\s*\}\);", page), (
        "the screen no longer asks for the URL's page and word, so the pager's numbers would govern "
        "nothing and the box would be a filter over rows the server already narrowed")

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
    # The pager's label reads from the locale table now, so the gate accepts the
    # key the page reads rather than the English copy it used to carry.
    assert re.search(r'label=(\{t\("interviews\.paginationLabel"\)\}|"interview sessions")', block), \
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
        r"const lastPage = sessions\.data \? lastPageOf\(total, sessions\.data\.size\) : 0;",
        page), (
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
    # 70.4 bound the board's word beside the card filter, so one more optional name sits
    # between the filter and the window. What this case measures is the window: the two
    # defaults `PAGE_SIZE` restates must not have moved with it.
    assert re.search(r'@RequestParam\(required = false\) UUID applicationId, '
                     r'@RequestParam\(required = false\) String q, '
                     r'@RequestParam\(defaultValue = "0"\) int page, '
                     r'@RequestParam\(defaultValue = "20"\) int size\)', controller), (
        f"the route's own window moved, so the board's PAGE_SIZE restates a different "
        f"number: {controller[controller.index('@GetMapping'):][:220]}")
    assert "return interviews.list(user.id(), page, size, applicationId, q);" in controller, (
        "the handler no longer forwards the request's own page and size to the service, so "
        "the window the board asks for would be decided elsewhere")
    service = collapse(java(SERVICE))
    assert ("sessions.findPage(userId, applicationId, needle, Paging.of(page, size).pageable())"
            in service), (
        "the list no longer comes back clamped, so a `?size=` past the ceiling would reach "
        "the query unbounded")
    # The order used to be spelled in the derived method's name; one query carries it now, so
    # that is where the claim is read. Without the id tiebreaker two rehearsals begun in the
    # same instant could land on either side of a page boundary on the next request.
    assert "ORDER BY s.startedAt DESC, s.id ASC" in java(REPOSITORY), (
        "the board's read lost its total order, so pages of it would repeat or skip rows")


def test_the_board_narrows_to_a_card_when_the_url_names_one():
    """Case 5 (57.1): the drawer's rehearsals link, all the way down.

    The card's row links to `/interviews?application=<id>`; the board has to
    adopt that key from the URL, hand it to the hook, and let the reader widen
    the list again. A filter the page keeps in React state only would be lost
    on reload, and a filter the hook drops would page over the whole history
    under a link that promised one card's.
    """
    page = read(INTERVIEWS_PAGE)
    assert "const applicationId = state.application;" in page, (
        "the board no longer reads the card filter out of the URL state")
    # 70.5 put the word in the same request, so the tail of the board's call is where both
    # scopes are visible at once: a card filter the reader can only reach by dropping the words,
    # or a word that costs a second query, is the shape this pins out.
    assert re.search(r"applicationId,\n\s*q: state\.q,\n\s*\}\);", page), (
        "the hook is no longer handed the card filter and the word in one request, so a narrowed "
        "list would be the whole history -- or the word would be a second question")
    assert 't("interviews.filteredToApplication")' in page, (
        "nothing on the page says the list is narrowed")
    assert page.count("setUrl({ page: 0, application: undefined })") == 2, (
        "both the header action and the empty state have to widen the list again")

    hook = collapse(read(RESOURCES))
    assert "applicationId?: string;" in hook, (
        "the hook's params no longer name the card filter it forwards")

    controller = collapse(java(CONTROLLER))
    assert '@RequestParam(required = false) UUID applicationId' in controller, (
        "the route no longer binds the filter the board sends")
    service = collapse(java(SERVICE))
    assert ("sessions.findPage(userId, applicationId, needle, Paging.of(page, size).pageable())"
            in service), (
        "the card filter is no longer handed to the board's own read, so a narrowed list "
        "would be a second query -- or the whole history under a link that promised one card")
    # 70.4 collapsed the two derived reads into one, so "scoped by the caller and the card
    # together" is now a claim about the query: the user is the first scope and the card id is
    # an optional second one inside it, never a replacement for it.
    repo = collapse(java(REPOSITORY))
    assert "WHERE s.userId = :userId" in repo, (
        "the board's read is no longer scoped by the caller, so a guessed card id would answer "
        "somebody else's rehearsals")
    assert ":applicationId IS NULL OR s.applicationId = :applicationId" in repo, (
        "the narrowed read is not scoped by the caller and the card together")


def test_starting_a_rehearsal_from_a_cards_list_starts_it_for_that_card():
    """Case 6 (57.3): the filter is the context of the screen, so it is the context of the create.

    On `/interviews?application=<id>` the start button used to create a free
    session; the reader then landed on a runner whose report had no card, and
    the narrowed list they came from would not have shown the new session at
    all. The create now carries the filter whenever the board has one.
    """
    page = read(INTERVIEWS_PAGE)
    assert re.search(r"\{ mode, \.\.\.\(applicationId \? \{ applicationId \} : "
                     r"\{\}\) \},", page), (
        "the create no longer carries the card the list is narrowed to")


def test_the_board_asks_its_own_question_and_keeps_the_asking_apart_from_the_typing():
    """Case 7 (70.5): the box, its draft, and the three empties it can leave the reader with.

    The route has answered a word since 70.4; this is the reader that asks it. Two claims hold the
    box honest. The first is that the characters in it are not yet a question -- binding the input
    straight to the URL would make every keystroke a request and a cache entry, and the board would
    answer a word nobody had finished typing. The second is that the answer is not filtered here:
    the rows are one window of the matches, so a client-side pass over them would hide the
    rehearsals the server found on another page and leave the pager counting a set the screen is
    not showing.
    """
    page = read(INTERVIEWS_PAGE)
    assert 'role="search"' in page, (
        "the board no longer marks its question as a search, so a screen reader cannot find it")
    assert "const [word, setWord] = React.useState(state.q ?? \"\");" in page, (
        "the box is no longer its own state, so every keystroke asks the route a new question")
    assert "React.useEffect(() => setWord(state.q ?? \"\"), [state.q]);" in page, (
        "the box no longer follows the URL back, so a pasted or cleared link leaves words on the "
        "screen the board is not asking")
    assert re.search(r"const ask = \(value: string\) => "
                     r"setUrl\(\{ q: value\.trim\(\) \|\| undefined, page: 0 \}\);", page), (
        "asking no longer trims the box, resets the page, or leaves an empty question unasked")
    assert re.search(r"event\.preventDefault\(\);\n\s*ask\(word\);", page), (
        "submitting the form no longer asks the typed words, so the box is decoration")
    assert 'placeholder={t("interviews.searchPlaceholder")}' in page and \
           'aria-label={t("interviews.searchLabel")}' in page, (
        "the box's own copy no longer comes from the locale table, so one language would ask "
        "for a word the other never shows")

    # The way out of a question that found nothing is the question, not a create form.
    assert re.search(r"\.\.\.\(state\.q\b", page), (
        "the empty no longer branches on the word, so a board full of rehearsals none of which "
        "spells it would tell the reader nobody has ever rehearsed")
    assert 't("interviews.noMatch", { query: state.q })' in page and \
           't("interviews.noMatchDescription")' in page, (
        "the word's empty lost its own sentence")
    assert page.count('{t("interviews.clearSearch")}') == 2, (
        "both the box and the empty it can leave have to offer to clear the question")

    # And the answer arrives already narrowed: the board renders the rows it was given.
    assert "page.items.map((s) => {" in page, (
        "the board no longer renders the answer's own rows, so the pager beside it is counting a "
        "set the screen is not showing")
    rendered = collapse(page[page.index("{(page) =>"):])
    assert ".filter(" not in rendered, (
        "the board re-narrows the rows it was given, so it hides rehearsals the server found on "
        f"another page: {rendered[:120]}")
