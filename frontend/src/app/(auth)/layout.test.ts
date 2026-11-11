import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

/**
 * The auth door is the first surface an anonymous visitor reaches, so it must
 * carry the same designed visual language as the landing page — a gradient
 * accent, a glass preview card, and a staggered entrance — without trading away
 * reliability or readability on its LIGHT sidebar panel:
 *
 * - the entrance motion is CSS-only (`animate-fade-up` + an inline
 *   animation-delay), never an IntersectionObserver, so the marketing copy is in
 *   the very first paint and needs no JS to become visible;
 * - there is deliberately NO full-bleed aurora here: its blobs use
 *   `mix-blend-mode: screen`, which washes out on the light `bg-sidebar` panel
 *   (the landing hero is the place for it). The accent is the gradient text and
 *   a shimmer rule instead — legible on light and dark;
 * - every animated layer is decorative and the copy stays the real translated
 *   `t()` keys (no new hardcoded English);
 * - the form itself (`children`) is untouched and still fades up as before.
 *
 * Source contract rather than DOM snapshot: AuthLayout is a client component
 * wired to locale/theme providers; the claims are about which additive layers
 * are composed, which a static render would obscure.
 */
const LAYOUT = fileURLToPath(new URL("./layout.tsx", import.meta.url));
const GLOBALS = fileURLToPath(new URL("../globals.css", import.meta.url));
const layout = readFileSync(LAYOUT, "utf8");
const globals = readFileSync(GLOBALS, "utf8");

describe("the auth door carries the landing design language", () => {
  it("gives the brand accent a gradient treatment", () => {
    expect(layout).toContain("GradientText");
    expect(layout).toContain('import { GradientText } from "@/components/ui/gradient-text"');
  });

  it("floats the product preview on a glass surface", () => {
    expect(layout).toContain("glass");
    expect(layout).toContain("ProductPreview");
  });

  it("staggers the pillars with CSS animation-delay, not an IntersectionObserver", () => {
    expect(layout).toMatch(/animationDelay/);
    expect(layout).not.toContain("IntersectionObserver");
    expect(layout).not.toContain("components/ui/reveal");
    // The entrance utility is the existing CSS token, not a new inline keyframe.
    expect(layout).toContain("animate-fade-up");
    // The reader's motion preference stays authoritative (global reduced-motion rule).
    expect(globals).toContain("prefers-reduced-motion: reduce");
    expect(globals).toMatch(/\.gradient-text[^}]*animation: none/);
  });

  it("does not spread a screen-blended aurora over the light sidebar", () => {
    // A conscious rejection, pinned so a future copy-paste from the landing hero
    // does not wash out the light panel: aurora blobs are screen-blended.
    expect(layout).not.toContain("AuroraBackground");
    expect(globals).toMatch(/\.aurora-blob[^}]*mix-blend-mode: screen/);
  });

  it("does not invent copy or drop the translated pillars", () => {
    for (const key of ["auth.eyebrow", "auth.headline", "auth.description", "auth.quote"]) {
      expect(layout).toContain(`t("${key}")`);
    }
    expect(layout).toMatch(/PILLARS\s*:/);
    expect(layout).toContain("t(p.title)");
    expect(layout).toContain("t(p.text)");
    // The form is still mounted and still gets its fade-up entrance.
    expect(layout).toContain("{children}");
    expect(layout).toContain('className="animate-fade-up"');
  });
});
