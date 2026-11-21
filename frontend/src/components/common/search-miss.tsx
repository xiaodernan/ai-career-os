"use client";

import * as React from "react";

import { trackSearch } from "@/lib/hooks/attention";

/**
 * Epic 372 — records one anonymous search that found nothing.
 *
 * Rendered inside the palette's empty state, so it only ever exists when there
 * really were no results. It reports once per query: the debounced value is the
 * identity, and a re-render (the query changing back, a group arriving late) must
 * not write the same word twice.
 *
 * Renders nothing -- it is a sensor, not a surface.
 */
export function SearchMiss({ query, hits }: { query: string; hits: number }) {
  const reported = React.useRef<string | null>(null);

  React.useEffect(() => {
    if (hits > 0) return;
    const word = query.trim();
    if (word.length === 0) return;
    if (reported.current === word) return;
    reported.current = word;
    trackSearch(window.location.pathname, word, hits);
  }, [query, hits]);

  return null;
}
