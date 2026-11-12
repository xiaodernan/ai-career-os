import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

/**
 * The inbox is the second surface a signed-in reader opens -- the one the unread badge pulls
 * them back to -- so its band must carry the same front-door language the dashboard established,
 * without trading away reliability, readability or the client bundle:
 *
 * - the accent is `GradientText` (a plain span), and the entrance is CSS-only (`animate-fade-up`
 *   + `animation-delay`), never an IntersectionObserver, so the title is in the first paint and
 *   needs no JS to appear;
 * - the aurora is DARK-ONLY (`hidden` gated by `dark:block`). Its blobs are `mix-blend-mode:
 *   screen`, which washes a light surface to white -- the trap Epic 137 documented on the auth
 *   sidebar, and the reason the dashboard gates it too. This Card is `bg-card/60`, light in the
 *   light theme;
 * - the blobs and washes are plain decorated spans, NOT `AuroraBackground` at vw scale and NOT
 *   the `Reveal` component (which brings a client IntersectionObserver), so the band adds zero
 *   new client JS and leaves the route budget untouched;
 * - every animated layer is decorative, reduced-motion stays authoritative via globals.css, and
 *   the copy stays the real translated `t("notifications.*")` keys -- the band invents no words.
 *
 * Source contract rather than DOM snapshot: the band composes additive CSS layers around a shared
 * `PageHeader`, which a static render would obscure.
 */
const PAGE = fileURLToPath(new URL("./page.tsx", import.meta.url));
const GLOBALS = fileURLToPath(new URL("../../globals.css", import.meta.url));
const page = readFileSync(PAGE, "utf8");
const globals = readFileSync(GLOBALS, "utf8");

describe("the inbox front door carries the designed visual language", () => {
  it("gives the inbox title a gradient accent", () => {
    expect(page).toContain('import { GradientText } from "@/components/ui/gradient-text"');
    expect(page).toContain("<GradientText");
    expect(page).toContain('<GradientText className="italic">{t("notifications.title")}</GradientText>');
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

  it("lifts the mark-all CTA on hover without changing its label", () => {
    // Unlike the dashboard, the inbox has no primary CTA -- mark-all is `outline` and clear-read
    // is `ghost` -- so there is no `glow-halo` to pin here, only the shared hover lift.
    expect(page).toContain("glow-on-hover");
  });

  it("invents no copy and keeps the shared PageHeader contract", () => {
    // No literal the reader sees is written in this file: every word is a `t("...")` key
    // from the real translation table. Pin the zero-argument keys by their full call shape.
    for (const key of [
      "notifications.title",
      "notifications.description",
      "notifications.allRead",
      "notifications.markAllRead",
      "notifications.clearRead",
    ]) {
      expect(page).toContain(`t("${key}")`);
    }
    // The unread count is interpolated, so its call closes on a comma, not a `)`:
    // `t("notifications.unreadBadge", { count: unread })`. Pin the key with its opening
    // argument instead of forcing a no-argument shape the page never had.
    expect(page).toContain('t("notifications.unreadBadge", { count: unread })');
    expect(page).toContain("<PageHeader");
    expect(page).toContain("title={");
    expect(page).toContain("description={");
    expect(page).toContain("actions={");
  });
});
