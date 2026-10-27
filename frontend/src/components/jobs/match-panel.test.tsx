import { describe, expect, it, vi } from "vitest";
import * as React from "react";
import { renderToStaticMarkup } from "react-dom/server";

// Mutable through `vi.hoisted`, so both describes below can render the same panel for a different
// reader; a factory closing over a plain `let` would read it before the test file's body runs.
const reader = vi.hoisted(() => ({ locale: "en" as "en" | "zh" }));

vi.mock("@/lib/i18n/locale-context", () => ({
  useLocale: () => ({ locale: reader.locale, t: (key: string) => key, setLocale: () => {} }),
}));

import { MatchPanel } from "./match-panel";
import type { JobMatch } from "@/lib/api/types";

/**
 * The "computed <when>" line under a match score.
 *
 * It was built with `new Date(...).toLocaleString()` -- no argument, which means the *machine's*
 * locale rather than the reader's. On a zh-CN machine an English reader read "computed
 * 2026/10/28 14:05:00" on an English page; on an en-US machine a Chinese reader read the mirror
 * image of it. The panel is the shipped seam: the unit tests in format.test.ts pin the strings,
 * this renders the card and reads the stamp off it.
 */

const computed = new Date(2026, 9, 28, 14, 5).toISOString();
const match: JobMatch = {
  id: "m-1",
  overall: 72,
  matchedSkills: ["Kubernetes"],
  createdAt: computed,
};

describe("the match panel's computed stamp", () => {
  it("reads the day and the clock in the reader's language (zh)", () => {
    reader.locale = "zh";
    try {
      const html = renderToStaticMarkup(<MatchPanel match={match} />);
      // formatDateTime draws day + clock (no year): "10月28日 14:05".
      expect(html, "the stamp under a match score is the one date on this card").toContain("10月28日 14:05");
      expect(html, "a zh reader got the machine's slash date").not.toContain("2026/10/28");
    } finally {
      reader.locale = "en";
    }
  });

  it("reads them in English for an English reader (control)", () => {
    const html = renderToStaticMarkup(<MatchPanel match={match} />);
    expect(html).toMatch(/Oct 28, 02:05\sPM/);
    expect(html, "an en reader got a Chinese date under an English card").not.toContain("10月28日");
  });
});
