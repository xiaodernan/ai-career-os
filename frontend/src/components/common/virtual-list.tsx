"use client";

import * as React from "react";

/**
 * A windowed list for the longest read paths (Epic 141).
 *
 * The feeds that never stop growing -- the timeline above all -- drew every row on
 * screen whether or not the reader ever scrolled there. Past a few hundred rows
 * the DOM cost, the layout cost and the memo churn all show up in the same long
 * task, and a reader who opened the timeline to look at one recent event paid
 * for all ten thousand.
 *
 * This is deliberately small and deliberately fixed-height: a constant row height
 * needs no measurement, no per-row ResizeObserver and no estimate/correct dance,
 * and it draws exactly the rows a full render would. Variable-height rows belong
 * to the caller's full-render path, not to this component.
 *
 * ARIA: the rows keep `role="listitem"` via the `<li>` wrappers, with
 * `aria-setsize` and `aria-posinset`, so a screen reader is told there are N rows
 * and can announce position honestly even though only a window is in the DOM.
 */

export interface WindowInput {
  /** Total rows, not the rendered ones. */
  count: number;
  /** Current scroll offset of the scroll container, in px. */
  scrollTop: number;
  /** Measured client height of the scroll container, in px. */
  viewportHeight: number;
  /** Constant row height, in px. */
  rowHeight: number;
  /** Extra rows to render above and below the visible window. */
  overscan: number;
}

export interface WindowRange {
  /** First index in the DOM (inclusive). */
  start: number;
  /** First index NOT in the DOM (exclusive). */
  end: number;
  /** Total scrollable height of the list, in px. */
  totalHeight: number;
}

/**
 * The pure core, kept dependency- and hook-free so the arithmetic is trivial to
 * test in a runner with no layout.
 *
 * Both edges are clamped against the count, and a zero-height viewport (jsdom, or
 * a collapsed panel) yields a window anchored at the top of the list rather than an
 * empty one, so nothing ever renders zero rows while items exist.
 */
export function computeWindow({ count, scrollTop, viewportHeight, rowHeight, overscan }: WindowInput): WindowRange {
  if (count <= 0 || rowHeight <= 0) {
    return { start: 0, end: 0, totalHeight: 0 };
  }
  const top = Math.max(0, scrollTop);
  const firstVisible = Math.floor(top / rowHeight);
  const lastVisible = Math.floor((top + Math.max(0, viewportHeight)) / rowHeight);
  const start = Math.min(count - 1, Math.max(0, firstVisible - overscan));
  const end = Math.min(count, Math.max(firstVisible + 1, lastVisible + 1 + overscan));
  return { start, end, totalHeight: count * rowHeight };
}

export interface VirtualListProps<T> {
  items: readonly T[];
  /** Constant row height in px. Every row must honour it (no wrapping). */
  rowHeight: number;
  /** Extra rows above and below the fold; default 6. */
  overscan?: number;
  getKey: (item: T, index: number) => React.Key;
  renderItem: (item: T, index: number) => React.ReactNode;
  /** Class for the scroll container (the element with `overflow-y-auto`). */
  className?: string;
  /** Accessible name of the list itself. */
  "aria-label"?: string;
}

/**
 * The scroll container must be a scroll box (`overflow-y-auto`); the inner track
 * is sized to `count * rowHeight` and rows are absolutely positioned by index.
 * Do not put margins on the scroll container's direct children: the track owns
 * the geometry, a margin collapses into it and the math drifts.
 */
export function VirtualList<T>({
  items,
  rowHeight,
  overscan = 6,
  getKey,
  renderItem,
  className,
  "aria-label": ariaLabel,
}: VirtualListProps<T>) {
  const scrollRef = React.useRef<HTMLDivElement | null>(null);
  const [view, setView] = React.useState({ top: 0, height: 0 });

  React.useLayoutEffect(() => {
    const el = scrollRef.current;
    if (!el) return undefined;
    const measure = () => {
      const height = el.clientHeight;
      const top = el.scrollTop;
      setView((prev) => (prev.height === height && prev.top === top ? prev : { height, top }));
    };
    measure();
    if (typeof ResizeObserver !== "undefined") {
      const observer = new ResizeObserver(measure);
      observer.observe(el);
      return () => observer.disconnect();
    }
    return undefined;
  }, []);

  const onScroll = React.useCallback((event: React.UIEvent<HTMLDivElement>) => {
    const top = event.currentTarget.scrollTop;
    setView((prev) => (prev.top === top ? prev : { ...prev, top }));
  }, []);

  const { start, end, totalHeight } = computeWindow({
    count: items.length,
    scrollTop: view.top,
    viewportHeight: view.height,
    rowHeight,
    overscan,
  });

  return (
    <div ref={scrollRef} onScroll={onScroll} className={className}>
      <ol
        className="relative"
        aria-label={ariaLabel}
        style={{ height: totalHeight, margin: 0 }}
      >
        {items.slice(start, end).map((item, offset) => {
          const index = start + offset;
          return (
            <li
              key={getKey(item, index)}
              aria-setsize={items.length}
              aria-posinset={index + 1}
              className="absolute inset-x-0"
              style={{ top: index * rowHeight, height: rowHeight }}
            >
              {renderItem(item, index)}
            </li>
          );
        })}
      </ol>
    </div>
  );
}
