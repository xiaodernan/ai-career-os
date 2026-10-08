import { describe, expect, it } from "vitest";

import { lastPageOf, pageWindow } from "./page-window";

describe("lastPageOf", () => {
  it("is the last page a partial final window still fills", () => {
    expect(lastPageOf(35, 20)).toBe(1);
    expect(lastPageOf(40, 20)).toBe(1);
  });
  it("keeps a short set on the first page", () => {
    expect(lastPageOf(5, 20)).toBe(0);
  });
  it("puts an empty set on the first page too", () => {
    expect(lastPageOf(0, 20)).toBe(0);
  });
  it("floors the divisor at 1, because a normalizer payload can report size 0", () => {
    // Without the floor this is -1 (a page before the first) or NaN; every page would read
    // as past-the-end and the board would correct itself into nothing.
    expect(lastPageOf(35, 0)).toBe(34);
    expect(lastPageOf(0, 0)).toBe(0);
  });
});

describe("pageWindow", () => {
  it("reports the first window of a multi-page set", () => {
    expect(pageWindow(0, 20, 35)).toEqual({ page: 0, pageCount: 2, from: 1, to: 20 });
  });
  it("reports the short final window", () => {
    expect(pageWindow(1, 20, 35)).toEqual({ page: 1, pageCount: 2, from: 21, to: 35 });
  });
  it("clamps a past-the-end page to the last page that exists", () => {
    // ?page=5 over 35 rows: the old inline formula printed 101-30 of 35 for the frame
    // before the screen's correction effect ran.
    expect(pageWindow(5, 20, 35)).toEqual({ page: 1, pageCount: 2, from: 21, to: 35 });
  });
  it("clamps a negative page to the first", () => {
    expect(pageWindow(-3, 20, 35)).toEqual({ page: 0, pageCount: 2, from: 1, to: 20 });
  });
  it("stands on one page when the set is empty", () => {
    expect(pageWindow(0, 20, 0)).toEqual({ page: 0, pageCount: 1, from: 0, to: 0 });
    expect(pageWindow(3, 20, 0)).toEqual({ page: 0, pageCount: 1, from: 0, to: 0 });
  });
  it("treats an exact multiple as a full last page, not an empty one", () => {
    expect(pageWindow(1, 20, 40)).toEqual({ page: 1, pageCount: 2, from: 21, to: 40 });
    expect(pageWindow(2, 20, 40)).toEqual({ page: 1, pageCount: 2, from: 21, to: 40 });
  });
});
