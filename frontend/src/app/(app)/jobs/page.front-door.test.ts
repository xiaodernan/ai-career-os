import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

/**
 * The job board is the highest-frequency signed-in surface after the dashboard and the inbox
 * -- and the one whose primary action already leads into the AI copilot -- so its band must
 * carry the same front-door language, without trading away reliability, readability or the
 * client bundle:
 *
 * - the accent is `GradientText` (a plain span), and the entrance is CSS-only (`animate-fade-up`
 *   + `animation-delay`), never an IntersectionObserver, so the title is in the first paint and
 *   needs no JS to appear;
 * - the aurora is DARK-ONLY (`hidden` gated by `dark:block`). Its blobs are `mix-blend-mode:
 *   screen`, which washes a light surface to white -- the trap Epic 137 documented on the auth
 *   sidebar, and the reason the dashboard and inbox gate it too. This Card is `bg-card/60`, light
 *   in the light theme;
 * - the blobs and washes are plain decorated spans, NOT `AuroraBackground` at vw scale and NOT
 *   the `Reveal` component (which brings a client IntersectionObserver), so the band adds zero
 *   new client JS and leaves the route budget untouched;
 * - the primary `variant="ai"` CTA carries both the shared hover lift and the AI halo, the
 *   same two-layer affordance the dashboard's primary CTA uses;
 * - every animated layer is decorative, reduced-motion stays authoritative via globals.css, and
 *   the copy stays the real translated `t("jobs.*")` keys -- the band invents no words.
 *
 * Source contract rather than DOM snapshot: the band composes additive CSS layers around a shared
 * `PageHeader`, which a static render would obscure.
 */
const PAGE = fileURLToPath(new URL("./page.tsx", import.meta.url));
const GLOBALS = fileURLToPath(new URL("../../globals.css", import.meta.url));
const page = readFileSync(PAGE, "utf8");
const globals = readFileSync(GLOBALS, "utf8");

describe("the job board front door carries the designed visual language", () => {
  it("gives the job board title a gradient accent", () => {
    expect(page).toContain('import { GradientText } from "@/components/ui/gradient-text"');
    expect(page).toContain("<GradientText");
    expect(page).toContain('<GradientText className="italic">{t("jobs.title")}</GradientText>');
  });

  it("crowns the band with a shimmer hairline", () => {
    expect(page).toContain("shimmer-rule");
  });

  it("staggers the entrance with CSS animation-delay, not an IntersectionObserver", () => {
    expect(page).toMatch(/animationDelay/);
    expect(page).toContain("animate-fade-up");
    expect(page).not.toMatch(/new IntersectionObserver\s*\(/); // no actual observer...
    expect(page).not.toContain("components/ui/reveal");        // ...and no Reveal import
    expect(page).not.toContain("AuroraBackground");
  });

  it("keeps the aurora dark-only so screen-blend never washes the light theme", () => {
    // The band is bg-card/60, light in the light theme. A screen-blended blob
    // composited there goes white; `hidden` + `dark:block` is the gate that makes
    // the drift safe. Pin both halves so a future edit cannot drop the guard.
    expect(page).toContain("aurora-blob");
    expect(page).toMatch(/hidden[^"]*dark:block|dark:block/);
    expect(page).toMatch(/aurora-blob[^"']*opacity-30/); // tamed for a short band
    expect(globals).toMatch(/\.aurora-blob[^}]*mix-blend-mode: screen/);
  });

  it("lets the reader's motion preference stay authoritative", () => {
    expect(globals).toContain("prefers-reduced-motion: reduce");
    expect(globals).toMatch(/\.aurora-blob[^}]*animation: none/);
    expect(globals).toMatch(/\.gradient-text[^}]*animation: none/);
  });

  it("lifts the primary AI CTA on hover and gives it the AI halo", () => {
    // Unlike the inbox, the job board has a `variant="ai"` primary CTA, so it carries
    // both layers the dashboard established: `glow-halo` (the AI affordance) and
    // `glow-on-hover` (the shared lift).
    expect(page).toContain("glow-on-hover");
    expect(page).toContain("glow-halo");
  });

  it("invents no copy and keeps the shared PageHeader contract", () => {
    // No literal the reader sees is written in this file: every word is a `t("...")` key
    // from the real translation table. Pin the zero-argument keys by their full call shape.
    for (const key of [
      "jobs.title",
      "jobs.description",
      "jobs.researchRoles",
    ]) {
      expect(page).toContain(`t("${key}")`);
    }
    expect(page).toContain("<PageHeader");
    expect(page).toContain("title={");
    expect(page).toContain("description={");
    expect(page).toContain("actions={");
  });
});
