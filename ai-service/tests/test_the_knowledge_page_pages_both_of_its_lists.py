"""#223: the knowledge page pages both of its lists -- the sixth and seventh windows.

#195 measured both knowledge hooks asking `{ size: 50 }` where their routes bind
`defaultValue = "20"`, and both callers passing no window at all: the sources list
rendered fifty rows with no pager and no reader of `total`, the notes panel the same.
The knowledge page is the screen where this bites differently from the other boards --
it holds two independent lists at once (sources through the page's own ModuleView,
notes through the panel component's), and one of them is filterable from the URL
(`?src=`, the citation focus, which narrows the sources to one document). Page the
wrong half and a citation link lands on an empty focus; page them together and the two
lists drift against each other.

Both lists now ask `{ page, size: PAGE_SIZE }` with PAGE_SIZE restating the route's own
20, and each keeps its own index in the URL: `?page=` for sources (the key the page's
existing `useUrlState` already owns beside `src`) and `?npage=` for notes -- two lists
on one screen ask two questions, and the notes panel owns its own URL state rather
than borrowing the page's. Each runs #219's past-the-end correction over its own
answer, and each pager arrives through ModuleView's opt-in footer (#222) gated on the
window that list serves. The sources pager is additionally gated on `!src`: under the
citation focus the answer is one document, and a pager over a one-row focus is noise.

The two hooks differ in how the window arrives, and that difference is pinned rather
than smoothed over: `useKnowledgeSources` keeps `live` and `documentId` positional and
takes the window as a third parameter; `useKnowledgeNotes` takes `params?` like every
other list hook. #228 moved both literals to the route's own 20, so the window each
hook sends on its only path is now the window its route defaults to.
"""

import re
from pathlib import Path

TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parent.parent

FRONT = ROOT / "frontend" / "src"
JAVA = ROOT / "backend" / "src" / "main" / "java"
RESOURCES = FRONT / "lib" / "hooks" / "resources.ts"
KNOWLEDGE_PAGE = FRONT / "app" / "(app)" / "knowledge" / "page.tsx"
NOTES_PANEL = FRONT / "components" / "knowledge" / "notes-panel.tsx"
MODULE_VIEW = FRONT / "components" / "common" / "module-view.tsx"
CONTROLLER = "com/careeros/knowledge/web/KnowledgeController.java"
SERVICE = "com/careeros/knowledge/service/KnowledgeService.java"


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


def test_the_sources_hook_takes_the_window_as_a_third_parameter():
    """Case 1: `live` and `documentId` stay positional; the window arrives third."""
    body = function_body(read(RESOURCES), "export function useKnowledgeSources(")
    assert re.search(r"export function useKnowledgeSources\(live = false, documentId\?: string,\n"
                     r"\s*params\?: \{ page\?: number; size\?: number \}\)", body), (
        f"the hook lost its third window parameter, so the sources list cannot ask for a "
        f"page: {collapse(body)[:150]}")
    assert re.search(r'queryKey: \["knowledge", "sources", live \? "live" : "once", '
                     r'documentId \?\? null, params\]', body), (
        f"the cache no longer separates pages, so page 1 would answer from page 0's entry: "
        f"{collapse(body)[:170]}")
    assert re.search(r"api\.get<unknown>\(endpoints\.knowledge,\s*"
                     r"\{ size: 20, documentId, \.\.\.\(params \?\? \{\}\) \}", collapse(body)), (
        f"the caller's window is no longer spread over the literal, so an asked-for page "
        f"would never reach the wire: {collapse(body)}")
    assert hook_calls("useKnowledgeSources") == [
        ("app/(app)/knowledge/page.tsx", "true, src, { page: state.page, size: PAGE_SIZE }"),
    ], f"the call sites moved: {hook_calls('useKnowledgeSources')}"


def test_the_notes_hook_takes_the_window_the_way_every_other_list_hook_does():
    """Case 2: `params?` on the notes reader, with the panel's call site spending it."""
    body = function_body(read(RESOURCES), "export function useKnowledgeNotes(")
    assert re.search(r"export function useKnowledgeNotes\("
                     r"params\?: \{ page\?: number; size\?: number \}\)", body), (
        f"the hook lost its window parameters, so the notes list cannot ask for a page: "
        f"{collapse(body)[:140]}")
    assert re.search(r'queryKey: \["knowledge", "notes", params\]', body), (
        f"the cache no longer separates pages, so page 1 would answer from page 0's entry: "
        f"{collapse(body)[:160]}")
    assert re.search(r"api\.get<unknown>\(endpoints\.knowledgeNotes, "
                     r"\{ size: 20, \.\.\.\(params \?\? \{\}\) \}\)", collapse(body)), (
        f"the caller's window is no longer spread over the literal, so an asked-for page "
        f"would never reach the wire: {collapse(body)}")
    assert hook_calls("useKnowledgeNotes") == [
        ("components/knowledge/notes-panel.tsx", "{ page: state.npage, size: PAGE_SIZE }"),
    ], f"the call sites moved: {hook_calls('useKnowledgeNotes')}"


def test_the_sources_pager_lives_on_the_page_url_and_hides_under_the_citation_focus():
    """Case 3: `?page=` beside `?src=`, the request, the correction, the focus gate."""
    page = read(KNOWLEDGE_PAGE)
    pinned = re.search(r"const PAGE_SIZE = (\d+);", page)
    assert pinned and int(pinned.group(1)) == 20, (
        f"the window the sources list asks for is {pinned and pinned.group(1)}, not the "
        "route's own default this case measures it against")
    assert re.search(r"const \[state, setUrl\] = useUrlState<\{ src\?: string; page: number \}>\(\n"
                     r"\s*\{ src: undefined, page: 0 \},\n"
                     r"\s*\{ numericKeys: \[\"page\"\] \}", page), (
        "the page index no longer lives in the URL beside the citation focus, so a shared "
        "list link always opens page 0")
    assert re.search(r"const sources = useKnowledgeSources\(true, src, "
                     r"\{ page: state\.page, size: PAGE_SIZE \}\);", page), (
        "the screen no longer asks for the URL's page, so the pager's numbers would govern nothing")
    assert re.search(r"const total = sources\.data\?\.total \?\? 0;", page), (
        "the formula's numerator is no longer the answer's total")
    assert re.search(
        r"const lastPage = sources\.data \? lastPageOf\(total, sources\.data\.size\) : 0;",
        page), (
        "the page no longer derives lastPage from the answer's own window and total, so a "
        "shared past-the-end page would stay empty")
    assert re.search(
        r"React\.useLayoutEffect\(\(\) => \{\n"
        r"\s*if \(sources\.data && state\.page > lastPage\) setUrl\(\{ page: lastPage \}\);\n"
        r"\s*\}, \[sources\.data, state\.page, lastPage, setUrl\]\);", page), (
        "no layout effect corrects a past-the-end URL page from the answer, so the stale "
        "empty copy can paint before the correction runs")
    at = page.index("<Pagination")
    block = page[at:page.index("/>", at)]
    assert re.search(r"page=\{sources\.data\?\.page \?\? state\.page\}", block), (
        "the pager's page index is no longer the answer's")
    assert re.search(r"size=\{PAGE_SIZE\}", block) and "data?.size" not in block \
        and "data.size" not in block, (
        f"the pager no longer takes the window the list asks with: {collapse(block)}")
    assert re.search(r"total=\{total\}", block) and re.search(r'label="sources"', block), (
        "the pager's row count or label moved off the envelope")
    assert re.search(r"!src && total > PAGE_SIZE && \(", page), (
        "the pager is no longer gated by both the focus and the window it serves, so a "
        "one-row citation focus would render a pager, or a short list would render one")


def test_the_notes_pager_lives_on_its_own_url_key_and_its_own_answer():
    """Case 4: `?npage=` in the panel, the request, the correction, the pager's numbers."""
    panel = read(NOTES_PANEL)
    pinned = re.search(r"const PAGE_SIZE = (\d+);", panel)
    assert pinned and int(pinned.group(1)) == 20, (
        f"the window the notes list asks for is {pinned and pinned.group(1)}, not the "
        "route's own default this case measures it against")
    assert re.search(r"const PAGE_DEFAULTS: \{ npage: number \} = \{ npage: 0 \};", panel), (
        "the defaults object is no longer the module-level const `setUrl` needs to stay stable")
    assert re.search(r"const \[state, setUrl\] = useUrlState<\{ npage: number \}>\(\n"
                     r"\s*PAGE_DEFAULTS,\n"
                     r"\s*\{ numericKeys: \[\"npage\"\] \}\n"
                     r"\s*\);", panel), (
        "the notes page index no longer lives in the URL under its own key, so it would "
        "share the sources list's index")
    assert re.search(r"const notes = useKnowledgeNotes\(\{ page: state\.npage, size: PAGE_SIZE \}\);",
                     panel), (
        "the panel no longer asks for the URL's page, so the pager's numbers would govern nothing")
    assert re.search(r"const total = notes\.data\?\.total \?\? 0;", panel), (
        "the formula's numerator is no longer the answer's total")
    assert re.search(
        r"const lastPage = notes\.data \? lastPageOf\(total, notes\.data\.size\) : 0;",
        panel), (
        "the panel no longer derives lastPage from the answer's own window and total, so a "
        "shared past-the-end page would stay empty")
    assert re.search(
        r"React\.useLayoutEffect\(\(\) => \{\n"
        r"\s*if \(notes\.data && state\.npage > lastPage\) setUrl\(\{ npage: lastPage \}\);\n"
        r"\s*\}, \[notes\.data, state\.npage, lastPage, setUrl\]\);", panel), (
        "no layout effect corrects a past-the-end URL page from the answer, so the stale "
        "empty copy can paint before the correction runs")
    at = panel.index("<Pagination")
    block = panel[at:panel.index("/>", at)]
    assert re.search(r"page=\{notes\.data\?\.page \?\? state\.npage\}", block), (
        "the pager's page index is no longer the answer's")
    assert re.search(r"size=\{PAGE_SIZE\}", block) and "data?.size" not in block \
        and "data.size" not in block, (
        f"the pager no longer takes the window the list asks with: {collapse(block)}")
    assert re.search(r"total=\{total\}", block) and re.search(r'label="notes"', block), (
        "the pager's row count or label moved off the envelope")
    assert re.search(r"onPageChange=\{\(page\) => \{\n"
                     r"\s*setUrl\(\{ npage: page \}\);", block), (
        "the pager no longer writes the notes list's own URL key, so the two lists would "
        "page together")


def test_both_routes_bind_the_window_the_two_lists_restate_and_order_their_rows():
    """Case 5: the defaults both PAGE_SIZEs restate, the clamps, the two orderings."""
    controller = collapse(java(CONTROLLER))
    assert re.search(r'@GetMapping\("/sources"\).*?@RequestParam\(defaultValue = "0"\) int page, '
                     r'@RequestParam\(defaultValue = "20"\) int size, '
                     r'@RequestParam\(required = false\) UUID documentId', controller, re.S), (
        "the sources route's own window moved, so the page's PAGE_SIZE restates a different number")
    assert re.search(r'@GetMapping\("/notes"\).*?@RequestParam\(defaultValue = "0"\) int page, '
                     r'@RequestParam\(defaultValue = "20"\) int size\)', controller, re.S), (
        "the notes route's own window moved, so the panel's PAGE_SIZE restates a different number")
    service = collapse(java(SERVICE))
    assert ("sources.findByUserIdOrderByCreatedAtDescIdAsc(userId, paging.pageable())" in service
            and "sources.findByUserIdAndDocumentIdOrderByCreatedAtDescIdAsc(userId, documentId, "
                "paging.pageable())" in service), (
        "the sources query no longer comes back clamped and ordered in both branches, so "
        "pages of it would repeat or skip rows")
    assert "notes.findByUserIdOrderByUpdatedAtDescIdAsc(userId, Paging.of(page, size).pageable())" \
        in service, (
        "the notes query no longer comes back clamped and ordered, so pages of it would "
        "repeat or skip rows")
    assert "{footer}" in read(MODULE_VIEW), (
        "the shared shell no longer renders the footer slot both pagers arrive through")
