/**
 * The window arithmetic a pager and its past-the-end correction share.
 *
 * #219 gave every board the same correction -- a page past the last one is an empty window
 * over a real total, so the URL is rewritten to the last page that exists -- and the rule
 * was written out in full on every screen: `Math.max(0, Math.ceil(total / Math.max(1,
 * size)) - 1)`, nine times, each under a comment explaining the divisor. Nine copies of one
 * rule are nine chances to drift, and the drift is silent: a screen that floors the divisor
 * differently corrects to a different page than the pager it renders. `lastPageOf` is the
 * rule, once.
 *
 * `pageWindow` is what the pager itself needs: the same last page, plus the row range it may
 * honestly print. A past-the-end page used to render "101-30 of 35" -- `from` computed from
 * the URL's page, `to` clamped to the total -- for the frame before the screen's correction
 * effect ran, and forever on a screen without one. It now reports the last real page's rows.
 *
 * The divisor is floored at 1 because a normalizer payload can report `size: 0`; a zero
 * divisor would make every page the last page and hide the whole board.
 */

export interface PageWindow {
  /** The page the other fields describe: `page` clamped into `0..pageCount - 1`. */
  page: number;
  /** How many pages exist -- at least 1, so an empty board still has a page to stand on. */
  pageCount: number;
  /** 1-based index of the first row on `page`; 0 when there are no rows at all. */
  from: number;
  /** 1-based index of the last row on `page`, never beyond `total`. */
  to: number;
}

/** Index of the last page a `total`-row set fills at `size` rows per page. */
export function lastPageOf(total: number, size: number): number {
  return Math.max(0, Math.ceil(total / Math.max(1, size)) - 1);
}

/** The window a pager may print for `page`, an out-of-range page clamped to the last one. */
export function pageWindow(page: number, size: number, total: number): PageWindow {
  const pageCount = lastPageOf(total, size) + 1;
  const shown = Math.min(Math.max(page, 0), pageCount - 1);
  return {
    page: shown,
    pageCount,
    from: total === 0 ? 0 : shown * size + 1,
    to: Math.min(total, (shown + 1) * size),
  };
}
