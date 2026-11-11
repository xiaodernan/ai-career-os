import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

/**
 * Detail links prefetch on hover and on keyboard focus (Epic 142).
 *
 * The two hottest detail entries in the product -- the job row and the resume row --
 * stretch across the whole card or sit behind a single "open" button. Next's Link
 * auto-prefetches on hover in production but not on keyboard focus, so the reader
 * tabbing to the row gets a cold page every time. The sidebar's warm-on-intent closes
 * that gap for the nav (Epic 123); this closes it for the rows that lead to detail.
 *
 * A source contract, like the sidebar's own: the wiring cannot be observed from
 * markup -- a handler nobody attaches is a warm nobody gets, and a refactor that
 * drops one of the two handlers goes red here.
 */

const read = (rel: string) =>
  readFileSync(fileURLToPath(new URL(rel, import.meta.url)), "utf-8");

describe("detail routes warm on hover and focus", () => {
  it("the hook binds the href at call time, per link", () => {
    const hook = read("./use-warm-link.ts");
    expect(hook).toContain("(href: string) => () => router.prefetch(href)");
    expect(hook).toContain("router.prefetch(href)");
    // It uses the App Router, like the rest of this app.
    expect(hook).toContain('from "next/navigation"');
    expect(hook).toContain("useRouter");
  });

  it("the job card warms the detail route on both gestures", () => {
    const card = read("../../components/jobs/job-card.tsx");
    expect(card).toContain("useWarmLink");
    expect(card).toMatch(/onMouseEnter=\{warm\(to\)\}/);
    expect(card).toMatch(/onFocus=\{warm\(to\)\}/);
  });

  it("the resume list warms both doors on both gestures", () => {
    const page = read("../../app/(app)/resumes/page.tsx");
    expect(page).toContain("useWarmLink");
    // Two Link sites (row title and the Open button), both warmed.
    expect((page.match(/onMouseEnter=\{warm\(`/g) ?? []).length).toBe(2);
    expect((page.match(/onFocus=\{warm\(`/g) ?? []).length).toBe(2);
  });
});
