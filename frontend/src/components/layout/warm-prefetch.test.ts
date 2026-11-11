import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

/**
 * The sidebar warms a route before the reader clicks it (Epic 123).
 *
 * Next's Link auto-prefetches on hover in production, but not on keyboard
 * focus — a reader tabbing the nav got a cold page every time they pressed
 * Enter. The sidebar therefore calls `router.prefetch(href)` on both
 * `onMouseEnter` and `onFocus`. The prefetch itself is idempotent, so this
 * layers on top of the framework rather than fighting it.
 *
 * This gate reads the source because the behaviour cannot be observed from
 * markup: a handler nobody wires is a warm nobody gets. If a refactor drops
 * either handler, this goes red.
 */

const SOURCE = readFileSync(
  fileURLToPath(new URL("./sidebar.tsx", import.meta.url)),
  "utf-8"
);

describe("the sidebar warms routes before the click", () => {
  it("prefetches on hover", () => {
    expect(SOURCE).toMatch(/onMouseEnter=\{warm\(item\.href\)\}/);
  });

  it("prefetches on keyboard focus", () => {
    expect(SOURCE).toMatch(/onFocus=\{warm\(item\.href\)\}/);
  });

  it("prefetches through the router, not a hand-rolled fetch", () => {
    expect(SOURCE).toContain("router.prefetch(href)");
    // The handler must be bound per href, not to a fixed route.
    expect(SOURCE).toContain("(href: string) => () => router.prefetch(href)");
  });

  it("uses the App Router's router (App Router only, pages router has none)", () => {
    expect(SOURCE).toContain('from "next/navigation"');
    expect(SOURCE).toContain("useRouter");
  });
});
