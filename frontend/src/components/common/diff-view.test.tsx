import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import * as React from "react";

import { DiffView } from "./diff-view";
import { LocaleProvider } from "@/lib/i18n/locale-context";

/**
 * The tailoring diff's statistics chips.
 *
 * `tailor()` returns `stats: {accepted, rejected}` and the chip used to split the wire
 * key on underscores, so a Chinese reader saw `accepted: 2` above badges that already
 * spoke their language. The fixture is the producer's own two-counter shape.
 */
function render(locale: "en" | "zh", stats: Record<string, unknown>): string {
  return renderToStaticMarkup(
    <LocaleProvider initialLocale={locale}>
      <DiffView
        accepted={[{ id: "a1", section: "experience", after: "Shipped the API" }]}
        stats={stats}
      />
    </LocaleProvider>
  );
}

/**
 * The statistics list itself, not the whole card.
 *
 * The page-wide text also contains "Applied" in a change row's AI badge and "已采纳"
 * inside the section heading "已采纳的改动", so a whole-markup `toContain` would pass
 * while the chip still spelled the wire key. The chips are the only list with an
 * accessible name.
 */
function chips(html: string): string {
  const list = html.match(/<ul[^>]*aria-label="[^"]*"[^>]*>([\s\S]*?)<\/ul>/);
  if (!list) throw new Error("the statistics list is missing");
  return list[1];
}

describe("the diff view's statistics chips", () => {
  it("names each counter in the reader's language", () => {
    const zh = chips(render("zh", { accepted: 2, rejected: 1 }));
    expect(zh).toContain("已采纳");
    expect(zh).toContain("已否决");
    expect(zh).not.toContain("accepted");
    expect(zh).not.toContain("rejected");

    const en = chips(render("en", { accepted: 2, rejected: 1 }));
    expect(en).toContain("Applied");
    expect(en).toContain("Rejected");
  });

  it("keeps a counter the roster does not know in its own spelling", () => {
    expect(chips(render("zh", { unchanged: 3 }))).toContain("Unchanged");
  });
});
