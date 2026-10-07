"""#219: a past-the-end page corrects itself before its empty copy can paint.

#218's own gate (`test_applications_deep_link_reaches_any_page.py`) closed on the residual it
did not fix: a shared `?page=99` over two pages of rows lands on the shared shell's empty state
-- "Pipeline is empty" through `ModuleView`, "The job board is quiet" through `QueryBoundary` --
with the pager unreachable until the URL is edited by hand. Both boards answer from the server's
window, and the stale page is a real answer: an empty `items` under a real `total` (Spring Data
builds the `Page` with the requested index whatever the offset; `Paging`'s docstring even states
the contract, "a page past the end is simply empty"). The answer is also what corrects it --
`lastPage` divides the answer's own `total` by the answer's own `size` (the window that really
produced the rows: `Paging.of` may have clamped it, and `normalizePage` can report 0 when its
`size` field is absent from an empty window, hence the `Math.max(1, ...)` floor), and a layout
effect rewrites the URL page when the requested one is past that end. A `useLayoutEffect` rather
than a plain effect because the stale commit paints its empty copy first: React flushes a layout
effect's state update before the browser paints, so the wrong screen is replaced, not seen.

The Saved tab needs no second mechanism: its window is computed client-side
(`filterAndPaginate`) and already clamps the page index, so the correction there writes the page
the clamp already chose -- the URL heals, the screen does not move. `?size=` policy and the
pagers' own numbers stay owner decisions (#194, #195); this file pins only the correction.
"""

import re
from pathlib import Path

TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parent.parent

FRONT = ROOT / "frontend" / "src"
JAVA = ROOT / "backend" / "src" / "main" / "java"
APPS_PAGE = FRONT / "app" / "(app)" / "applications" / "page.tsx"
JOBS_PAGE = FRONT / "app" / "(app)" / "jobs" / "page.tsx"
NORMALIZE = FRONT / "lib" / "api" / "normalize.ts"
JOB_FILTER = FRONT / "lib" / "job-filter.ts"
PAGING = JAVA / "com" / "careeros" / "common" / "Paging.java"

SIZE_ZERO_SOURCE = re.compile(r'size: num\(raw, "size"\) \?\? arr\.length,')
PAGING_FLOOR = re.compile(r"Math\.min\(Math\.max\(size, 1\), MAX_PAGE_SIZE\)")


def read(path: Path) -> str:
    """Shipped text with LF endings; `git archive` hands out CRLF on this host."""
    return path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")


def test_the_applications_board_corrects_a_past_the_end_page_before_it_paints():
    """Case 1: the answer's own window divides, and a layout effect rewrites the URL page."""
    page = read(APPS_PAGE)
    assert re.search(r"const total = applications\.data\?\.total \?\? 0;", page), (
        "the formula's numerator is no longer the answer's total")
    assert re.search(
        r"const lastPage = applications\.data\n"
        r"\s*\? Math\.max\(0, Math\.ceil\(total / Math\.max\(1, applications\.data\.size\)\) - 1\)\n"
        r"\s*: 0;", page), (
        "the board no longer derives lastPage from the answer's own window and total")
    assert re.search(
        r"React\.useLayoutEffect\(\(\) => \{\n"
        r"\s*if \(applications\.data && state\.page > lastPage\) setUrl\(\{ page: lastPage \}\);\n"
        r"\s*\}, \[applications\.data, state\.page, lastPage, setUrl\]\);", page), (
        "no layout effect corrects a past-the-end URL page from the answer, so the stale "
        "empty copy can paint before the correction runs")


def test_the_jobs_board_corrects_the_same_way_over_the_window_both_tabs_share():
    """Case 2: `listView` is the jobs answer on Discover and the client window on Saved."""
    page = read(JOBS_PAGE)
    assert re.search(r"const total = listView\.data\?\.total \?\? 0;", page), (
        "the formula's numerator is no longer the shared window's total")
    assert re.search(
        r"const lastPage = listView\.data\n"
        r"\s*\? Math\.max\(0, Math\.ceil\(total / Math\.max\(1, listView\.data\.size\)\) - 1\)\n"
        r"\s*: 0;", page), (
        "the board no longer derives lastPage from the answer's own window and total")
    assert re.search(
        r"React\.useLayoutEffect\(\(\) => \{\n"
        r"\s*if \(listView\.data && filters\.page > lastPage\) setFilters\(\{ page: lastPage \}\);\n"
        r"\s*\}, \[listView\.data, filters\.page, lastPage, setFilters\]\);", page), (
        "no layout effect corrects a past-the-end URL page from the shared window, so the "
        "stale empty copy can paint before the correction runs")


def test_the_divisor_floors_at_one_because_the_empty_window_can_report_size_zero():
    """Case 3: a `size` of 0 is a frontend normalizer report on the very payload the
    correction runs on (the absent field falls back to `arr.length` of an empty list);
    the server's floor keeps every real window at >= 1, so `Math.max(1, ...)` costs
    nothing there and keeps the correction alive where it matters."""
    normalize = read(NORMALIZE)
    assert SIZE_ZERO_SOURCE.search(normalize), (
        "normalizePage no longer falls back to arr.length, so the 0-size seed this floor "
        "absorbs may have moved")
    paging = read(PAGING)
    assert PAGING_FLOOR.search(paging), (
        "Paging.of no longer floors the window at 1, so a 0-size report is no longer a "
        "frontend-only story")
    for page_file, divisor in ((APPS_PAGE, "applications.data.size"),
                               (JOBS_PAGE, "listView.data.size")):
        text = read(page_file)
        assert f"Math.max(1, {divisor})" in text, (
            f"{page_file.name} divides by the raw {divisor}: an empty window reporting 0 "
            "turns lastPage into 0/0 and the correction dies silently on its own trigger")


def test_the_saved_tabs_window_already_clamps_so_the_same_correction_is_idempotent_there():
    """Case 4: on Saved the answer is `filterAndPaginate`'s window, whose page index is
    clamped to the same last page the correction computes -- so the effect's write there
    names the page the clamp already chose (#194 case 7 pins the clamp itself; this binds
    it as the correction's Saved half, reachable through the `listView` swap)."""
    filtered = read(JOB_FILTER)
    assert re.search(r"const lastPage = Math\.max\(0, Math\.ceil\(filtered\.length / size\) - 1\);",
                     filtered), "filterAndPaginate no longer derives its own last page"
    assert re.search(r"const page = Math\.min\(Math\.max\(0, filters\.page \?\? 0\), lastPage\);",
                     filtered), (
        "the client window no longer clamps the page index, so the Saved correction would "
        "stop being idempotent there")
    page = read(JOBS_PAGE)
    assert re.search(
        r"const savedPage = React\.useMemo\(\n"
        r"\s*\(\) => \(saved\.data \? filterAndPaginate\(saved\.data\.items, filters\) : undefined\),",
        page), "the Saved window is no longer the answer the correction reads"
    assert re.search(
        r"const listView = tab === \"saved\" \? \(\{ \.\.\.saved, data: savedPage \} as typeof saved\) : jobs;",
        page), "the correction no longer reaches the Saved window through this swap"
