import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

/**
 * The bypass has two halves and neither shows up in a screenshot: a link rendered after the
 * sidebar is still a link, and a `#main` href with no `id="main"` scrolls nowhere at all. So
 * the shell is read as text and both halves are held in place.
 *
 * The component's own doc comment names the classes it rejects (`sr-only`, `not-sr-only`) and
 * the attribute it refuses (`tabIndex={-1}`), so every class and attribute assertion below runs
 * against `JSX` -- the text after `export function` -- and never against the whole file. A
 * whole-file `not.toContain` would pass or fail on prose, which is how the first draft of this
 * suite failed on its own documentation.
 */
const SHELL = readFileSync(new URL("../../app/(app)/layout.tsx", import.meta.url), "utf8");
const LINK = readFileSync(new URL("./skip-link.tsx", import.meta.url), "utf8");
const JSX = LINK.slice(LINK.indexOf("export function"));

describe("the app shell's skip link", () => {
  it("is the shell's first focusable element, ahead of the sidebar and the topbar", () => {
    const link = SHELL.indexOf("<SkipLink />");
    expect(link, "the shell no longer renders a skip link").toBeGreaterThan(-1);
    expect(link).toBeLessThan(SHELL.indexOf("<Sidebar />"));
    expect(link).toBeLessThan(SHELL.indexOf("<Topbar />"));
  });

  it("points at the landmark the shell actually renders", () => {
    expect(JSX).toContain("href=\"#main\"");
    expect(SHELL).toMatch(/<main[^>]*\bid="main"/);
  });

  it("makes the target focusable, so the next Tab starts inside the content", () => {
    expect(SHELL).toMatch(/<main[^>]*tabIndex=\{-1\}/);
  });

  it("keeps the -1 on the target, not on itself", () => {
    expect(JSX).not.toMatch(/<a[^>]*tabIndex/);
  });

  it("stays out of the way until it takes focus", () => {
    expect(JSX).toContain("-translate-y-16");
    expect(JSX).toContain("focus:translate-y-0");
  });

  it("hides itself by translating, not by clipping", () => {
    expect(JSX).not.toContain("sr-only");
    expect(JSX).not.toContain("not-sr-only");
  });

  it("is never hidden from assistive technology", () => {
    expect(JSX).not.toContain("aria-hidden");
  });
});
