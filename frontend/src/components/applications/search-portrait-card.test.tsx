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

import { SearchPortraitCard } from "./search-portrait-card";

/**
 * 376: the shape of one reader's search -- a description, never a score.
 *
 * An empty board draws nothing rather than an invented shape, and a single application
 * is a fact rather than a pattern.
 */

const NOW = new Date("2026-11-22T12:00:00Z");
const day = (n: number) => new Date(NOW.getTime() - n * 86_400_000).toISOString();

describe("SearchPortraitCard", () => {
  it("describes a burst with the week it happened in", () => {
    const html = renderToStaticMarkup(
      <SearchPortraitCard
        input={{
          applications: [{ at: day(2) }, { at: day(1) }, { at: day(1) }, { at: day(0) }, { at: day(40) }],
          now: NOW,
        }}
      />
    );
    expect(html).toContain("applications.portraitBurstTitle");
    expect(html).toContain("applications.portraitBurstBody");
    // The sentence names the busiest week, which is what makes it a portrait rather
    // than a count.
    expect(html).toContain("Nov 20, 2026");
  });

  it("describes a long tail without ranking it against a burst", () => {
    const html = renderToStaticMarkup(
      <SearchPortraitCard
        input={{
          applications: [{ at: day(150) }, { at: day(100) }, { at: day(50) }, { at: day(0) }],
          now: NOW,
        }}
      />
    );
    expect(html).toContain("applications.portraitLongTailTitle");
    expect(html).not.toContain("portraitBurstTitle");
  });

  it("calls one application a fact, not a pattern", () => {
    const html = renderToStaticMarkup(
      <SearchPortraitCard input={{ applications: [{ at: day(3) }], now: NOW }} />
    );
    expect(html).toContain("applications.portraitSingleTitle");
    expect(html).toContain("applications.portraitSingleBody");
  });

  it("draws nothing at all for an empty board", () => {
    // Inventing a shape for nobody's search would be the exact failure this product
    // exists to avoid.
    expect(renderToStaticMarkup(<SearchPortraitCard input={{ applications: [], now: NOW }} />)).toBe("");
  });
});
