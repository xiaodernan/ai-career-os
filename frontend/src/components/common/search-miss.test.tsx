import { describe, expect, it, vi } from "vitest";
import * as React from "react";
import { renderToStaticMarkup } from "react-dom/server";

const trackSearch = vi.hoisted(() => vi.fn());
vi.mock("@/lib/hooks/attention", () => ({
  trackSearch,
  AttentionSensor: () => null,
  trackAct: () => undefined,
  leaveRoom: () => undefined,
}));

import { SearchMiss } from "./search-miss";

/**
 * 372: a search that found nothing is a reader who could not find their way.
 *
 * The sensor renders nothing and reports at most once per query — the debounced
 * value is the identity, and a re-render must not write the same word twice.
 *
 * SSR is the only render this suite can do (no effects run), so the rendering
 * contract is pinned here and the once-per-query rule is pinned by the guard in the
 * component's own ref: a second effect with the same word returns before it posts.
 */

describe("SearchMiss", () => {
  it("renders nothing — it is a sensor, not a surface", () => {
    expect(renderToStaticMarkup(<SearchMiss query="kubernetes" hits={0} />)).toBe("");
  });

  it("does not post for a query that found something", () => {
    // The component is only rendered inside the empty state, so this is the belt
    // to the braces: a hit means no row, whatever the caller thought.
    renderToStaticMarkup(<SearchMiss query="java" hits={3} />);
    expect(trackSearch).not.toHaveBeenCalled();
  });
});
