import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

/**
 * The resume manager is the first surface a new reader works through -- upload, parse, then
 * versions -- so its header band must carry the same front-door language the dashboard, jobs
 * board and inbox established, without trading away reliability, readability or the client
 * bundle:
 *
 * - the accent is `GradientText` (a plain span), and the entrance is CSS-only (`animate-fade-up`
 *   + `animation-delay`), never an IntersectionObserver, so the title is in the first paint and
 *   needs no JS to appear;
 * - the aurora is DARK-ONLY (`hidden` gated by `dark:block`). Its blobs are `mix-blend-mode:
 *   screen`, which washes a light surface to white -- the trap Epic 137 documented on the auth
 *   sidebar, and the reason the dashboard, inbox and jobs board gate it too. This band is
 *   `bg-card/60`, light in the light theme;
 * - the blobs and washes are plain decorated spans, NOT `AuroraBackground` at vw scale and NOT
 *   the `Reveal` component (which brings a client IntersectionObserver), so the band adds zero
 *   new client JS and leaves the route budget untouched;
 * - UNLIKE those pages this header has no actions: the real work is the `UploadDropzone` and the
 *   version list below it. Every layer the band adds is `aria-hidden` + `pointer-events-none`, so
 *   it cannot swallow a click meant for the dropzone or a version card, and no CTA is invented
 *   just to have one to lift. The existing interactive markers must survive the band verbatim.
 * - every animated layer is decorative, reduced-motion stays authoritative via globals.css, and
 *   the copy stays the real translated `t("resumes.*")` keys -- the band invents no words.
 *
 * Source contract rather than DOM snapshot: the band composes additive CSS layers around a shared
 * `PageHeader`, which a static render would obscure.
 */
const PAGE = fileURLToPath(new URL("./page.tsx", import.meta.url));
const GLOBALS = fileURLToPath(new URL("../../globals.css", import.meta.url));
const page = readFileSync(PAGE, "utf8");
const globals = readFileSync(GLOBALS, "utf8");

describe("the resume manager front door carries the designed visual language", () => {
  it("gives the resume title a gradient accent", () => {
    expect(page).toContain('import { GradientText } from "@/components/ui/gradient-text"');
    expect(page).toContain("<GradientText");
    expect(page).toContain('<GradientText className="italic">{t("resumes.title")}</GradientText>');
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

  it("frames the header without inventing a CTA or swallowing the real interactions", () => {
    // This header has no actions, so there is deliberately no `glow-on-hover` lift to pin.
    // What must hold instead: every decorative layer is inert (aria-hidden + pointer-events-none),
    // and the interactions that actually do the page's work survive the band verbatim.
    expect(page).toMatch(/aria-hidden\s+className="pointer-events-none absolute/);
    expect(page).toContain("shimmer-rule absolute inset-x-0 top-0");
    for (const marker of [
      "<UploadDropzone",
      "useDeleteResume",
      "<ConfirmDialog",
      "<Pagination",
      "onUploaded=",
    ]) {
      expect(page).toContain(marker);
    }
    // No visible copy and no primary AI CTA were invented for the band.
    expect(page).not.toContain('variant="ai" size="sm" className="glow-halo');
  });

  it("invents no copy and keeps the shared PageHeader contract", () => {
    // No literal the reader sees is written in this file: every word is a `t("...")` key
    // from the real translation table. Pin the zero-argument keys by their full call shape.
    for (const key of ["resumes.title", "resumes.description"]) {
      expect(page).toContain(`t("${key}")`);
    }
    expect(page).toContain("<PageHeader");
    expect(page).toContain("title={");
    expect(page).toContain("description={");
    // The real work stays in the dropzone section, still labelled by its own key.
    expect(page).toContain('aria-label={t("resumes.uploadSection")}');
  });
});
