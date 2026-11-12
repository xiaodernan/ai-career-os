import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

/**
 * The shared PageHeader's front door (Epic 164): the band is opt-in on purpose,
 * so a call site that does not ask for it cannot inherit the designed surface by
 * accident — the five bespoke shells keep ownership of the band they pin in their
 * own contracts, and every other page now gets the same language without one copy
 * of markup per call site.
 *
 * Source contract rather than DOM snapshot: the band composes additive CSS layers
 * around a shared inner block; what must not drift is recorded here — the band is
 * CSS-only, the aurora is dark-only, and every decorative layer is inert.
 */

const SOURCE = readFileSync(
  fileURLToPath(new URL("./page-header.tsx", import.meta.url)),
  "utf-8"
);
const GLOBALS = readFileSync(
  fileURLToPath(new URL("../../app/globals.css", import.meta.url)),
  "utf-8"
);

describe("PageHeader's front door", () => {
  it("renders the plain block by default — the band never sneaks past the opt-in", () => {
    expect(SOURCE).toContain("if (!frontDoor)");
    expect(SOURCE).toContain("return header;");
  });

  it("crowns the band with the shimmer hairline when asked", () => {
    expect(SOURCE).toContain("shimmer-rule absolute inset-x-0 top-0");
  });

  it("keeps the aurora dark-only and tamed, the jobs/dashboard invariant", () => {
    expect(SOURCE).toMatch(/hidden[^"]*dark:block|dark:block/);
    expect(SOURCE).toMatch(/aurora-blob[^"']*opacity-30/);
    expect(GLOBALS).toMatch(/\.aurora-blob[^}]*mix-blend-mode: screen/);
    expect(SOURCE).not.toContain("components/ui/aurora");
    expect(SOURCE).not.toMatch(/new IntersectionObserver\s*\(/);
    expect(SOURCE).not.toContain("components/ui/reveal");
  });

  it("frames the header with inert decoration only — nothing a reader can hit", () => {
    // Every aurora/wash layer is aria-hidden + pointer-events-none.
    const layers = SOURCE.match(/aria-hidden[\s\S]*?pointer-events-none/g) ?? [];
    expect(layers.length).toBeGreaterThanOrEqual(3);
    expect(SOURCE).toContain("pointer-events-none absolute inset-0");
  });

  it("staggers the entrance with CSS animation-delay, not an observer", () => {
    expect(SOURCE).toContain("animate-fade-up");
    expect(SOURCE).toMatch(/animationDelay: "90ms"/);
    expect(SOURCE).toMatch(/animationDelay: "160ms"/);
  });

  it("invents no copy, no actions and no route of its own", () => {
    // The band ships values and gradients; every word is still the consumer's key.
    expect(SOURCE).not.toMatch(/aurora-blob[^"]*glow/);
    expect(GLOBALS).toMatch(/prefers-reduced-motion: reduce/);
    expect(GLOBALS).toMatch(/\.aurora-blob[^}]*animation: none/);
    expect(GLOBALS).toMatch(/\.gradient-text[^}]*animation: none/);
  });

  it("keeps the inner block's own contract for consumers that asked, byte for byte", () => {
    // Consumers pass title/description/actions through verbatim; the band adds nothing
    // to the API and nothing to the order the heading lands on.
    expect(SOURCE).toContain('className="font-serif text-display-md');
    expect(SOURCE).toContain("{description && <p");
    expect(SOURCE).toContain("{actions && (");
  });
});
