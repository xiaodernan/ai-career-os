"""#218: the applications board pages, and the dashboard's deep link lands wherever the card lives.

#195 measured the board asking for exactly `Paging.MAX_PAGE_SIZE` with no pager and reading no
`total`, so its 101st application was simply not there; the dashboard's attention rows link a card
with `?application=<id>`, and the rows that need attention are the stale ones (`updatedAt` 14 days
old), which sort last (`updatedAt DESC`) -- the exact tail one full window cuts off. The board now
pages, and the window half of that move is pinned by the two window gates (#195 case 7 asks the
request and the pager's render, #194 case 4 the pager's numbers). What neither asks is this file:
the deep link. Two claims, every end derived from shipped text -- the by-id read exists and spends
the by-id route, and the screen resolves the id through the page in hand *and* a direct fetch for
every page it has not fetched.

A past-the-end page (`?page=99` with two pages of rows) used to land on the shared shell's empty
state with the pager unreachable until the URL was edited -- the jobs board's too. #219's
`test_a_past_the_end_page_corrects_itself.py` now pins the correction that follows on both boards.
"""

import re
from pathlib import Path

TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parent.parent

JAVA = ROOT / "backend" / "src" / "main" / "java"
FRONT = ROOT / "frontend" / "src"
RESOURCES = FRONT / "lib" / "hooks" / "resources.ts"
ENDPOINTS = FRONT / "lib" / "api" / "endpoints.ts"
APPS_PAGE = FRONT / "app" / "(app)" / "applications" / "page.tsx"
#: 43.1 moved the attention row -- and the link it writes -- out of the dashboard page into
#: this component, so case 2 reads the row the page renders rather than the page's own text.
ATTENTION_ROW = FRONT / "components" / "dashboard" / "attention-row.tsx"
CONTROLLER = "com/careeros/application/web/ApplicationController.java"

LINK_PARAM = "application="


def read(path: Path) -> str:
    """Shipped text with LF endings; `git archive` hands out CRLF on this host."""
    return path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")


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


def test_the_by_id_route_has_a_reader_and_the_hook_spends_that_route():
    """Case 1: no browser code read `GET /applications/{id}` before #218; the fallback does."""
    resources = read(RESOURCES)
    body = function_body(resources, "export function useApplication(id: string | null) {")
    keys = sorted(set(re.findall(r"endpoints\.(\w+)", body)))
    assert keys == ["application"], (
        f"the fallback spends {keys}, so it is not the by-id read this case claims")
    assert 'queryKey: ["application", id],' in body, body
    assert "enabled: Boolean(id)," in body, (
        f"the hook no longer refuses a null id, so a spend of /applications/null is reachable: {body}")
    assert "async (): Promise<Application>" in body and "normalizeApplication" in body, body

    declared = re.search(r"application: \(id: string\) => `/applications/\$\{seg\(id\)\}`",
                         read(ENDPOINTS))
    assert declared, "endpoints.ts no longer declares the by-id route this hook spends"

    controller = read(JAVA / CONTROLLER)
    assert re.search(r'@GetMapping\("/\{id\}"\)\s*\n\s*public ApplicationItem get\(', controller), (
        "the by-id GET no longer answers an ApplicationItem, so the record this hook normalizes "
        "is not one any route promises")


def test_the_deep_link_reads_the_page_in_hand_first_and_fetches_the_rest():
    """Case 2: the dashboard's attention row writes the param; the board answers from its page or a fetch."""
    row = read(ATTENTION_ROW)
    link = "/applications?" + LINK_PARAM + "${encodeURIComponent(row.id)}"
    assert link in row, (
        f"the attention row no longer writes the {LINK_PARAM!r} param this file reads")

    page = read(APPS_PAGE)
    assert "useUrlState<{ application?: string; page: number }>(" in page, page
    assert "const deepLinkId = state.application;" in page, page
    assert re.search(r"const inPage = deepLinkId\s*\n\s*\? applications\.data\?\.items\.find"
                     r"\(\(a\) => a\.id === deepLinkId\)\s*\n\s*: undefined;", page), (
        "the page no longer looks for the linked card among the rows it has")
    assert ("const outside = useApplication(deepLinkId && applications.data && !inPage "
            "? deepLinkId : null);") in page, (
        "the fallback fetch no longer waits for the page in hand to miss the card first")
    assert "const found = inPage ?? outside.data;" in page, (
        "the editor no longer opens for a card found off this page")
    assert "if (found) setDialog({ open: true, app: found });" in page, page
    assert "if (!open && state.application) setUrl({ application: undefined });" in page, (
        "closing the editor no longer clears the param, so a refetch could reopen it")
