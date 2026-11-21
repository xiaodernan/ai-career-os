import { describe, expect, it, vi } from "vitest";
import * as React from "react";
import { renderToStaticMarkup } from "react-dom/server";

vi.mock("@/lib/i18n/locale-context", () => ({
  useLocale: () => ({
    locale: "en",
    t: (key: string, vars?: Record<string, unknown>) =>
      key + (vars ? ":" + JSON.stringify(vars) : ""),
  }),
}));

import { RhythmCard } from "./rhythm-card";

/**
 * 374: a nudge, never a score.
 *
 * The bands are the product's own, and the reader who has never rehearsed gets a
 * different sentence rather than the same one with a bigger number.
 */

const NOW = new Date("2026-11-22T12:00:00Z");
const daysAgo = (days: number) => new Date(NOW.getTime() - days * 86_400_000).toISOString();

describe("RhythmCard", () => {
  it("says the habit is warm inside a week", () => {
    const html = renderToStaticMarkup(
      <RhythmCard input={{ sessions: [{ at: daysAgo(2) }], now: NOW }} />
    );
    expect(html).toContain("interviews.rhythmFreshTitle");
    expect(html).toContain("interviews.rhythmFreshBody");
  });

  it("names the last rehearsal's own date once the habit has cooled", () => {
    // The sentence is the reader's data, not a derived number.
    const html = renderToStaticMarkup(
      <RhythmCard input={{ sessions: [{ at: daysAgo(40) }], now: NOW }} />
    );
    expect(html).toContain("interviews.rhythmStaleTitle");
    expect(html).toContain("interviews.rhythmStaleBody");
  });

  it("gives a reader who has never rehearsed a different sentence", () => {
    // Not the same one with a bigger number: they have not started, and saying so
    // is a different thing from saying they fell behind.
    const html = renderToStaticMarkup(<RhythmCard input={{ sessions: [], now: NOW }} />);
    expect(html).toContain("interviews.rhythmNoneTitle");
    expect(html).toContain("interviews.rhythmNoneBody");
    expect(html).not.toContain("rhythmFreshTitle");
    expect(html).not.toContain("rhythmStaleTitle");
  });
});
