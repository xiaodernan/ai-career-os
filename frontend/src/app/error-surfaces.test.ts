import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

/**
 * The error boundaries carry the same failure-surface language (Epic 142).
 *
 * `error.tsx` (the per-route boundary) and `global-error.tsx` (the outermost
 * one, rendering its own `<html>` and importing globals.css itself) both were the
 * barest screens in the product. This pins both as source claims, the same shape as
 * the 404 and auth-door pins:
 *
 * - the aurora backdrop is decorative and hidden from AT;
 * - the entrance is CSS-only stagger (`animate-fade-up` + inline animationDelay),
 *   never an IntersectionObserver;
 * - zero new copy: every string is the translated keys the pages always had;
 * - the reset button takes the glow-halo + glow-on-hover pair;
 * - `global-error.tsx` still supplies its own `<html>`, `<body>` and globals.css
 *   import — the swap renders instead of the root layout, and the boundary that
 *   cannot assume the shell still has to stand alone.
 */
describe("the error boundaries carry the failure-surface language", () => {
  const read = (rel: string) =>
    readFileSync(fileURLToPath(new URL(rel, import.meta.url)), "utf-8");
  const ERROR = read("./error.tsx");
  const GLOBAL = read("./global-error.tsx");

  it("renders the decorative aurora backdrop on both boundaries, hidden from AT", () => {
    for (const SRC of [ERROR, GLOBAL]) {
      expect(SRC).toMatch(/aria-hidden className="aurora-bg/);
      expect(SRC).toContain("aurora-grid");
    }
  });

  it("enters with CSS-only stagger on both boundaries", () => {
    for (const SRC of [ERROR, GLOBAL]) {
      expect(SRC).toContain("animate-fade-up");
      expect(SRC).toMatch(/animationDelay: "\d+ms"/);
      expect(SRC).not.toMatch(/new IntersectionObserver/);
    }
  });

  it("keeps the same translated copy on both boundaries", () => {
    expect(ERROR).toContain('t("errors.brokeOnThisScreen")');
    expect(ERROR).toContain('t("errors.brokeOnThisScreenDescription")');
    expect(GLOBAL).toContain('t("errors.couldNotStart")');
    expect(GLOBAL).toContain('t("errors.couldNotStartDescription")');
    expect(GLOBAL).toContain('t("common.tryAgain")');
    expect(ERROR).toContain('t("common.tryAgain")');
  });

  it("keeps the glow-halo on the reset button on both boundaries", () => {
    expect(ERROR).toContain("glow-halo");
    expect(ERROR).toContain("glow-on-hover");
    expect(GLOBAL).toContain("glow-halo");
    expect(GLOBAL).toContain("glow-on-hover");
  });

  it("global-error still stands alone without the root shell", () => {
    // The whole reason this file exists: the root layout may be gone, so the
    // boundary must bring its own html/body/globals.css.
    expect(GLOBAL).toContain("<html");
    expect(GLOBAL).toMatch(/import "\.\/globals\.css"/);
    expect(GLOBAL).toContain("LocaleProvider");
    expect(ERROR).not.toContain("<html");
  });
});
