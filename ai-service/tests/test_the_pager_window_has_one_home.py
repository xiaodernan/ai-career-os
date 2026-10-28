"""The pager's window arithmetic lives in exactly one file, and every screen reads it there.

#219 shipped the past-the-end correction to every board by writing the rule out in full on
each screen -- `Math.max(0, Math.ceil(total / Math.max(1, size)) - 1)` under a comment
explaining the divisor -- and `Pagination` derived its own page count and row range with the
same formula spelled a third way. Ten copies of one rule, and the copies had already drifted:
the pager's `from`/`to` read the URL's page while its `pageCount` clamped the divisor, so a
page past the end printed "101-30 of 35" for the frame before the screen's correction effect
ran (and forever on a screen without one). The arithmetic now lives in
`frontend/src/lib/page-window.ts`, unit-tested by `page-window.test.ts`; this gate holds the
wiring so the copies cannot quietly come back:

* the pager component takes its window from the shared helper and computes nothing itself;
* no other file under `frontend/src` derives a page count from a total (the census that would
  have caught the ten copies);
* every board that runs the past-the-end correction names the shared helper, and the count is
  pinned (the ten server-window screens plus `job-filter.ts`, whose Saved tab clamps the
  same rule over a client-side set), so a new board means a new call site rather than an
  eleventh copy.
"""

from pathlib import Path

TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parent.parent
FRONT = ROOT / "frontend" / "src"
COMPONENT = FRONT / "components" / "common" / "pagination.tsx"
HELPER = FRONT / "lib" / "page-window.ts"
HELPER_TEST = FRONT / "lib" / "page-window.test.ts"

CORRECTION_SITES = 11


def read(path: Path) -> str:
    """Shipped text with LF endings; `git archive` hands out CRLF on this host."""
    return path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")


def frontend_sources() -> list[Path]:
    return sorted(p for p in FRONT.rglob("*.ts*") if p not in (HELPER, HELPER_TEST))


def test_the_pager_takes_its_window_from_the_shared_helper():
    text = read(COMPONENT)
    assert 'from "@/lib/page-window"' in text, (
        "pagination.tsx no longer imports the shared window helper")
    assert "pageWindow(page, size, total)" in text, (
        "pagination.tsx must derive its whole window from pageWindow(page, size, total)")
    assert "Math.ceil" not in text, (
        "pagination.tsx derives its own page count again -- the clamp inside pageWindow is "
        "what keeps a past-the-end page from advertising rows that do not exist")


def test_no_other_screen_derives_a_page_count_from_a_total():
    offenders = [str(p.relative_to(ROOT)) for p in frontend_sources()
                 if "Math.ceil" in read(p)]
    assert offenders == [], (
        f"these files compute a page count themselves instead of calling lastPageOf: "
        f"{offenders}")


def test_every_board_runs_the_correction_through_the_helper():
    callers = [p for p in frontend_sources() if "lastPageOf(" in read(p)]
    assert len(callers) == CORRECTION_SITES, (
        f"{len(callers)} screens call lastPageOf, pinned at {CORRECTION_SITES} -- a new "
        f"board either calls the helper or the pin moves with a reason")
    for p in callers:
        assert "Math.ceil" not in read(p), f"{p.name} still spells the formula out itself"


def test_the_helper_and_its_unit_test_both_exist():
    """Positive control: the census above passes trivially if the helper was never written."""
    assert HELPER.exists() and HELPER_TEST.exists()
    helper = read(HELPER)
    assert "export function lastPageOf" in helper
    assert "export function pageWindow" in helper
    cases = read(HELPER_TEST)
    for phrase in ("past-the-end", "negative", "empty set", "exact multiple"):
        assert phrase in cases, f"page-window.test.ts no longer pins the {phrase} case"
