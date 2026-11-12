import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

/**
 * The dashboard is the first surface a signed-in reader sees, so its front-door
 * band must carry the landing/auth design language — a gradient accent, a shimmer
 * hairline, a staggered CSS-only entrance and an ambient aurora — without trading
 * away reliability, readability or the client bundle:
 *
 * - entrance motion is CSS-only (`animate-fade-up` + inline `animation-delay`),
 *   never an IntersectionObserver, so the greeting is in the first paint and needs
 *   no JS to appear (the same contract the auth door pins);
 * - the aurora is DARK-ONLY (`hidden` gated by `dark:block`). Its blobs are
 *   `mix-blend-mode: screen`, which washes a light surface to white — the exact
 *   trap Epic 137 documented on the auth sidebar. Gating it means a light-theme
 *   reader gets the static token washes only; a dark-theme reader gets the drift.
 *   This is the deliberate evolution of auth's "no aurora at all" rejection;
 * - the blobs are plain decorated spans, NOT `AuroraBackground` at vw scale and
 *   NOT the `Reveal` component (which brings a client IntersectionObserver), so
 *   the band adds zero new client JS and leaves the 340 kB route budget untouched;
 * - every animated layer is decorative, reduced-motion stays authoritative via
 *   globals.css, and the copy stays the real translated `t("dashboard.*")` keys.
 *
 * Source contract rather than DOM snapshot: the band composes additive CSS layers
 * around a shared `PageHeader`, which a static render would obscure.
 */
const PAGE = fileURLToPath(new URL("./page.tsx", import.meta.url));
const GLOBALS = fileURLToPath(new URL("../../globals.css", import.meta.url));
const page = readFileSync(PAGE, "utf8");
const globals = readFileSync(GLOBALS, "utf8");

describe("the dashboard front door carries the designed visual language", () => {
  it("gives the greeting name a gradient accent", () => {
    expect(page).toContain('import { GradientText } from "@/components/ui/gradient-text"');
    expect(page).toContain("<GradientText");
    expect(page).not.toContain('className="italic text-primary"'); // the old flat accent is gone
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

  it("lifts both CTAs on hover without changing their labels", () => {
    expect(page).toContain("glow-on-hover");
    expect(page).toContain("glow-halo"); // the primary CTA keeps its halo
  });

  it("invents no copy and keeps the shared PageHeader contract", () => {
    for (const key of [
      "dashboard.description",
      "dashboard.askCopilot",
      "dashboard.openPipeline",
    ]) {
      expect(page).toContain(`t("${key}")`);
    }
    expect(page).toContain("<PageHeader");
    expect(page).toContain("title={");
    expect(page).toContain("description={");
    expect(page).toContain("actions={");
  });
});

describe("the recent-activity card reads the event log the backend sends", () => {
  // The mapper used to carry `recentActivity` across the wire and drop it at the browser boundary.
  // These pins keep the whole chain visible in one place: the payload field, the row component, and
  // the three copy keys that make the card -- plus its empty and error states -- say something real.
  it("wires the field, the row and the card's own copy", () => {
    expect(page).toContain('import { RecentActivityRow } from "@/components/dashboard/recent-activity"');
    expect(page).toContain("data?.recentActivity");
    expect(page).toContain("<RecentActivityRow");
    for (const key of [
      "dashboard.recentActivity",
      "dashboard.recentActivityDescription",
      "dashboard.noRecentActivity",
      "dashboard.noRecentActivityDescription",
      "dashboard.activityFailed",
    ]) {
      expect(page).toContain(`t("${key}")`);
    }
  });
});
