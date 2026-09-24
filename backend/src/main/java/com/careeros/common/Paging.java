package com.careeros.common;

import org.springframework.data.domain.PageRequest;

/**
 * The one place an outside paging coordinate becomes a query window.
 *
 * {@code page} and {@code size} arrive straight from the address bar, and every way of
 * spending them is total-or-throw, never total-or-empty: {@link PageRequest} rejects
 * {@code page < 0} and {@code size < 1} with {@code IllegalArgumentException}, and the job
 * search appends {@code LIMIT :limit OFFSET :offset} while binding those parameters only
 * when the limit is positive — so {@code ?size=0} leaves the statement referencing
 * parameters nobody bound, and {@code ?page=-1} reaches PostgreSQL as
 * {@code OFFSET -12}, which it rejects outright. Each of those lands in
 * {@code GlobalExceptionHandler.fallback} as a 500 "Internal server error": a typo in a
 * bookmark would be reported as our bug, exactly the mistake the handler's own comment
 * calls out for Jackson bodies.
 *
 * Clamping instead of rejecting keeps every request answerable: page 0 is the first page,
 * a page past the end is simply empty, and a window is always 1..{@link #MAX_PAGE_SIZE}
 * rows. The ceiling used to be hand-written at nine controllers and forgotten at
 * {@code GET /companies}' sibling paths; it lives here now, so a new list endpoint cannot
 * ask for it wrongly.
 */
public final class Paging {

    /** Rows one request may ask for. A caller wanting more pages pages. */
    public static final int MAX_PAGE_SIZE = 100;

    private Paging() {
    }

    /** A paging window that has already been made safe to spend. */
    public record Window(int page, int size) {

        /**
         * Rows to skip. Widened to {@code long} on purpose: the page is only floored here, not
         * capped, and {@code ?page=2000000000&size=100} overflows an {@code int} product into a
         * negative offset — which PostgreSQL rejects, putting the 500 right back.
         */
        public long offset() {
            return (long) page * size;
        }

        public PageRequest pageable() {
            return PageRequest.of(page, size);
        }
    }

    /** Floor the page at the first one; keep the window inside 1..{@link #MAX_PAGE_SIZE}. */
    public static Window of(int page, int size) {
        return new Window(Math.max(page, 0), Math.min(Math.max(size, 1), MAX_PAGE_SIZE));
    }

    /**
     * The first page of at most {@code size} rows — for callers that page by "recent" rather
     * than by request. Same ceiling, because an activity feed's {@code ?limit=} is a URL too.
     */
    public static PageRequest first(int size) {
        return of(0, size).pageable();
    }
}
