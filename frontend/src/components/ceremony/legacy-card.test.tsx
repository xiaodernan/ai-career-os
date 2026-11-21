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

import { LegacyCard } from "./legacy-card";

/**
 * 371: what this search leaves behind — and the silence when it leaves nothing.
 *
 * The card reads the ledgers the page already fetched, so it renders nothing at all
 * when the ledger is thin: a reader who did one thing should not be handed a
 * retrospective, and a card that invents a lesson is worse than no card.
 */

describe("LegacyCard", () => {
  it("names the material, the costliest stage and the lesson", () => {
    const html = renderToStaticMarkup(
      <LegacyCard
        input={{
          stages: { applied: 12, interview: 3 },
          rehearsals: 5,
          reportsWritten: 1,
          letters: 2,
          notesKept: 1,
          offers: 1,
        }}
      />
    );
    expect(html).toContain("legacy.title");
    expect(html).toContain("legacy.lessonUnfinishedTitle");
    expect(html).toContain("legacy.costliestStage");
    expect(html).toContain("legacy.reuseReportsTitle");
    expect(html).toContain('href="/interviews"');
    expect(html).toContain('href="/offers"');
  });

  it("draws nothing at all for a thin ledger", () => {
    expect(renderToStaticMarkup(<LegacyCard input={{}} />)).toBe("");
  });

  it("keeps the stage name through the locale, never a raw id", () => {
    // The board's ids are not the reader's words; the label comes from the table.
    const html = renderToStaticMarkup(
      <LegacyCard input={{ stages: { applied: 4 } }} />
    );
    expect(html).toContain("stages.applied");
  });
});
