import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

/**
 * The lost page of the brand (Epic 142).
 *
 * The 404 has always been the one surface every anonymous visitor is one bad link
 * away from, and it was a compass and two lines of copy -- not even the front-door
 * language the landing, auth doors and dashboard carry. This pins the redesign as
 * source claims, the same shape as the landing and auth-door pins:
 *
 * - the aurora backdrop is decorative and hidden from AT, with the grid masked to a
 *   shallow arc (never a full-bleed wash on the light theme);
 * - the ghost numeral is aria-hidden; the announcement the screen reader gets is the
 *   real translated heading, not a display glyph;
 * - the entrance is CSS-only stagger (`animate-fade-up` + inline animationDelay),
 *   never an IntersectionObserver -- the copy must be in the first paint;
 * - there is deliberately no new copy: every string is the same `t()` keys it always
 *   was -- the copy census is unaffected;
 * - the LocaleSwitcher stays top-right (the localization promise on a public page).
 */
describe("the 404 body carries the front-door language", () => {
  const SRC = readFileSync(fileURLToPath(new URL("./not-found-body.tsx", import.meta.url)), "utf-8");

  it("renders the decorative aurora backdrop, hidden from AT", () => {
    // The backdrop is decorative: the AT announcement is the heading, never a blob.
    expect(SRC).toMatch(/aria-hidden className="aurora-bg/);
    expect(SRC).not.toMatch(/>(Sign in|Get started|AI-native)</);
  });

  it("carries the ghost 404 as decoration, not as the announcement", () => {
    expect(SRC).toMatch(/aria-hidden[^>]*>[\s\S]*?404[\s\S]*?<\/div>/);
    expect(SRC).toContain('aria-hidden\n        className="pointer-events-none');
  });

  it("enters with CSS-only stagger, never an IntersectionObserver", () => {
    expect(SRC).toContain("animate-fade-up");
    expect(SRC).toMatch(/animationDelay: "\d+ms"/);
    expect(SRC).not.toMatch(/new IntersectionObserver/);
  });

  it("keeps the same translated copy (no new strings)", () => {
    expect(SRC).toContain('t("errors.notOnTheMap")');
    expect(SRC).toContain('t("errors.notOnTheMapDescription")');
    expect(SRC).toContain('t("common.backToDashboard")');
  });

  it("keeps the language switch reachable on the public page", () => {
    expect(SRC).toContain("LocaleSwitcher");
  });

  it("keeps the glow-halo accent on the CTA", () => {
    expect(SRC).toContain("glow-halo");
    expect(SRC).toContain("shimmer-rule");
  });
});
