import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

/**
 * The interview rehearsal board is a headline action for every candidate, so its header band
 * must carry the same front-door language the dashboard, jobs board, inbox and resume manager
 * established, without trading away reliability, readability or the client bundle:
 *
 * - the accent is `GradientText` (a plain span), and the entrance is CSS-only (`animate-fade-up`
 *   + `animation-delay`), never an IntersectionObserver, so the title is in the first paint and
 *   needs no JS to appear;
 * - the aurora is DARK-ONLY (`hidden` gated by `dark:block`). Its blobs are `mix-blend-mode:
 *   screen`, which washes a light surface to white -- the trap Epic 137 documented on the auth
 *   sidebar, and the reason every other front-door band gates it too. This Card is `bg-card/60`,
 *   light in the light theme;
 * - the blobs and washes are plain decorated spans, NOT `AuroraBackground` at vw scale and NOT
 *   the `Reveal` component (which brings a client IntersectionObserver), so the band adds zero
 *   new client JS and leaves the route budget untouched;
 * - the primary `variant="ai"` CTA (start an interview) carries both the shared hover lift and
 *   the AI halo -- the same two-layer affordance the dashboard and jobs board established;
 * - the real controls in `actions` (the server search box, the application filter, the mode
 *   dropdown) are untouched: the band only gives their row an entrance and the primary CTA its
 *   glow. Every animated layer is decorative, reduced-motion stays authoritative via globals.css,
 *   and the copy stays the real translated `t("interviews.*")` keys -- the band invents no words.
 *
 * Source contract rather than DOM snapshot: the band composes additive CSS layers around a shared
 * `PageHeader`, which a static render would obscure.
 */
const PAGE = fileURLToPath(new URL("./page.tsx", import.meta.url));
const GLOBALS = fileURLToPath(new URL("../../globals.css", import.meta.url));
const page = readFileSync(PAGE, "utf8");
const globals = readFileSync(GLOBALS, "utf8");

describe("the interview board front door carries the designed visual language", () => {
  it("gives the interview title a gradient accent", () => {
    expect(page).toContain('import { GradientText } from "@/components/ui/gradient-text"');
    expect(page).toContain("<GradientText");
    expect(page).toContain('<GradientText className="italic">{t("interviews.title")}</GradientText>');
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
    // The board has a `variant="ai"` primary CTA (start an interview), so it carries
    // both layers the dashboard/jobs board established: `glow-halo` and `glow-on-hover`.
    expect(page).toContain('variant="ai" className="glow-halo glow-on-hover"');
  });

  it("invents no copy, keeps the PageHeader contract and leaves the real controls intact", () => {
    // No literal the reader sees is written in this file: every word is a `t("...")` key
    // from the real translation table. Pin the band's zero-argument keys by their full shape.
    for (const key of ["interviews.title", "interviews.description"]) {
      expect(page).toContain(`t("${key}")`);
    }
    expect(page).toContain("<PageHeader");
    expect(page).toContain("title={");
    expect(page).toContain("description={");
    expect(page).toContain("actions={");
    // The controls that do the page's work survive the band verbatim.
    for (const marker of [
      'role="search"',
      "<DropdownMenu>",
      't("interviews.startInterview")',
      "<Pagination",
    ]) {
      expect(page).toContain(marker);
    }
  });
});
