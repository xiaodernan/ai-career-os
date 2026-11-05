import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import type * as React from "react";

vi.mock("@/lib/i18n/locale-context", () => ({
  useLocale: () => ({
    locale: "en",
    t: (key: string, vars?: Record<string, string | number>) =>
      vars ? `${key}|${JSON.stringify(vars)}` : key,
    setLocale: () => {},
  }),
}));

import { PracticeLine } from "./practice-line";

const render = (practice: React.ComponentProps<typeof PracticeLine>["practice"], applicationId?: string | null) =>
  renderToStaticMarkup(<PracticeLine practice={practice} applicationId={applicationId} />);

/** The markup escaped the stub's JSON quotes; the words are what matter here. */
const text = (html: string) => html.replace(/&quot;/g, '"').replace(/&amp;/g, "&");

describe("PracticeLine", () => {
  it("says nothing for a rehearsal that has no card", () => {
    expect(render(null, "app-1")).toBe("");
  });

  it("greets the card's first rehearsal without a count", () => {
    const html = render({ position: 1, count: 1 }, "app-1");
    expect(html).toContain("interviews.practice.first");
    expect(html).not.toContain('href="/interviews?application=');
  });

  it("names the position, the count and the rounded best score", () => {
    const html = render({ position: 2, count: 3, best: 84.4 }, "app-1");
    expect(text(html)).toContain('interviews.practice.progress|{"position":2,"count":3,"best":84}');
    expect(html).toContain('href="/interviews?application=app-1"');
  });

  it("keeps a history with no grade free of a score", () => {
    const html = render({ position: 2, count: 3 }, "app-1");
    expect(text(html)).toContain('interviews.practice.progressNoBest|{"position":2,"count":3}');
    expect(html).not.toContain("interviews.practice.progress|");
  });

  it("draws no door when the card id is missing", () => {
    const html = render({ position: 2, count: 3, best: 70 }, null);
    expect(text(html)).toContain("interviews.practice.progress|");
    expect(html).not.toContain('href="/interviews?application=');
  });
});
