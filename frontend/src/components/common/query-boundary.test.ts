// @vitest-environment node
import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { isEmptyPage } from "@/components/common/query-boundary";
import { normalizePage } from "@/lib/api/normalize";

/**
 * The judgment `QueryBoundary`/`SectionBoundary` make to choose between a list and
 * its designed empty state. It runs on payloads produced by `normalizePage`, so the
 * fixtures below are that function's real output rather than a hand-written shape.
 */
describe("isEmptyPage", () => {
  it("treats a 200-with-no-rows page as empty", () => {
    // This is the case the boundary used to miss: the payload is an object, so it
    // rendered `children` over a zero-row list and no screen ever showed its
    // "Nothing here yet" state.
    const page = normalizePage({ items: [], total: 0, page: 0, size: 20 }, (x) => x);
    expect(page.items).toEqual([]);
    expect(isEmptyPage(page)).toBe(true);
  });

  it("treats a bare array response the same way", () => {
    expect(isEmptyPage([])).toBe(true);
    expect(isEmptyPage([{ id: "a" }])).toBe(false);
    expect(isEmptyPage(normalizePage([{ id: "a" }], (x) => x))).toBe(false);
  });

  it("keeps a page that has rows", () => {
    expect(isEmptyPage(normalizePage({ items: [{ id: "a" }], total: 1 }, (x) => x))).toBe(false);
    // An out-of-range page index is still not "nothing to show": the rows exist.
    expect(isEmptyPage({ items: [{ id: "a" }], total: 30, page: 9, size: 12 })).toBe(false);
  });

  it("treats an unsettled query as empty", () => {
    expect(isEmptyPage(null)).toBe(true);
    expect(isEmptyPage(undefined)).toBe(true);
  });

  it("never guesses that a detail payload is empty", () => {
    expect(isEmptyPage({ id: "run-1", agent: "copilot", status: "succeeded" })).toBe(false);
    // A page-shaped object whose items are missing entirely is a contract break, not
    // an empty list; saying "Nothing here yet" would blame the user's data.
    expect(isEmptyPage({ total: 0 })).toBe(false);
    expect(isEmptyPage({ items: null })).toBe(false);
    expect(isEmptyPage("saved")).toBe(false);
  });
});

describe("the boundary's empty branch", () => {
  // React can't render in the node environment, so this guards the wiring only: the
  // predicate above must be the single judgment for both the body and the card box.
  const source = () =>
    readFileSync(new URL("./query-boundary.tsx", import.meta.url), "utf8");

  it("routes both empty checks through the one predicate", () => {
    const src = source();
    expect(src).toContain("if (isEmptyPage(query.data))");
    expect(src).toContain("!isEmptyPage(query.data)");
    expect(src).not.toMatch(/Array\.isArray\(query\.data\)/);
  });
});
