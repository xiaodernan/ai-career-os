import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

import { computeWindow, VirtualList } from "./virtual-list";

/**
 * Epic 141: the windowed list. The row count any reader can scroll is arbitrary,
 * so the part that must be right is the arithmetic, not the pixels:
 *
 * - the window at rest covers what the fold shows plus overscan, no more;
 * - scrolling to the middle selects a middle window, exact rows, no gaps;
 * - the two edges clamp: the top never renders before row 0, the tail never
 *   after the last row, and an exact-fit window is exact;
 * - zero sizes never produce a negative or empty window when items exist, and
 *   produce the honest empty triple when they don't;
 * - the scroll track reports the full height even though only a window is in the
 *   DOM, and every rendered row carries `aria-setsize`/`aria-posinset` so a
 *   screen reader is told the truth about how many rows there are.
 */
describe("computeWindow", () => {
  const base = { count: 1000, viewportHeight: 600, rowHeight: 72, overscan: 4 };

  it("covers the fold at rest and no more", () => {
    // lastVisible = floor(600/72) = 8; end = 8 + 1 + overscan.
    expect(computeWindow({ ...base, scrollTop: 0 })).toEqual({
      start: 0,
      end: 13,
      totalHeight: 1000 * 72,
    });
  });

  it("selects a middle window with no gaps or overlaps", () => {
    const { start, end, totalHeight } = computeWindow({ ...base, scrollTop: 72 * 100 });
    expect(start).toBe(96);          // 100 - overscan
    expect(end).toBe(113);           // floor(7800/72) + 1 + overscan
    expect(end - start).toBe(17);
    expect(end).toBeGreaterThan(start);
    expect(totalHeight).toBe(72000);
  });

  it("clamps the tail at the end of the list", () => {
    const { start, end } = computeWindow({ ...base, scrollTop: 72 * 10000 });
    expect(end).toBe(1000);
    expect(start).toBe(999); // firstVisible is 10000; the start clamps to the tail
  });

  it("clamps the head and never goes negative", () => {
    expect(computeWindow({ ...base, scrollTop: -50 }).start).toBe(0);
    expect(computeWindow({ ...base, scrollTop: 0 }).start).toBe(0);
  });

  it("is honest about zero rows and zero heights", () => {
    expect(computeWindow({ count: 0, scrollTop: 0, viewportHeight: 600, rowHeight: 72, overscan: 4 })).toEqual({
      start: 0,
      end: 0,
      totalHeight: 0,
    });
    // A collapsed panel (height 0) still anchors the window at the top.
    expect(computeWindow({ count: 50, scrollTop: 0, viewportHeight: 0, rowHeight: 72, overscan: 4 }).end).toBe(5);
    expect(computeWindow({ count: 50, scrollTop: 0, viewportHeight: 0, rowHeight: 72, overscan: 4 }).start).toBe(0);
  });

  it("never returns an empty window while rows exist", () => {
    const w = computeWindow({ count: 3, scrollTop: 7200, viewportHeight: 600, rowHeight: 72, overscan: 6 });
    expect(w.start).toBeLessThan(w.end);
    expect(w.end).toBe(3);
  });
});

describe("VirtualList (SSR markup)", () => {
  const items = Array.from({ length: 120 }, (_, i) => ({ id: `row-${i}`, label: `Row ${i}` }));

  it("renders a window at rest, with the full count announced honestly", () => {
    const html = renderToStaticMarkup(
      <VirtualList
        items={items}
        rowHeight={72}
        getKey={(item) => item.id}
        renderItem={(item) => <span>{item.label}</span>}
        aria-label="rows"
      />,
    );
    // SSR renders the at-rest window: fold (viewport 0 -> one row) + overscan.
    expect((html.match(/aria-posinset/g) ?? []).length).toBe(7);
    expect(html).toContain('aria-setsize="120"');
    expect(html).toContain('aria-posinset="1"');
    expect(html).toContain('aria-posinset="7"');
    expect(html).not.toContain("Row 9"); // outside the at-rest window
    // The track reserves the full height even though only a window is in the DOM.
    expect(html).toContain("height:8640px");
  });
});
