import { describe, expect, it } from "vitest";

import { SHAPE_MIN_COUNT, searchPortrait } from "./search-shape";

/**
 * 376: the shape of one reader's search.
 *
 * Two readers with the same count can have completely different searches, and the
 * count cannot tell them apart. The shapes are stated rather than derived, and every
 * degenerate input answers honestly: an empty ledger, a single row, a clock ahead of
 * the row.
 */

const NOW = new Date("2026-11-22T12:00:00Z");
const day = (n: number) => new Date(NOW.getTime() - n * 86_400_000).toISOString();

describe("searchPortrait", () => {
  it("reads the span from the first to the last application", () => {
    const out = searchPortrait({ applications: [{ at: day(30) }, { at: day(10) }, { at: day(0) }], now: NOW });
    expect(out.count).toBe(3);
    expect(out.spanDays).toBe(31);
  });

  it("finds the busiest seven-day window with a two-pointer walk", () => {
    // 4 of 6 inside three days is a burst; the walk must find that window rather
    // than whichever start it looked at first.
    const out = searchPortrait({
      applications: [{ at: day(20) }, { at: day(19) }, { at: day(18) }, { at: day(17) },
        { at: day(9) }, { at: day(1) }],
      now: NOW,
    });
    expect(out.busiest?.count).toBe(4);
    expect(out.shape).toBe("burst");
  });

  it("names a burst when most of the search landed in one week", () => {
    const out = searchPortrait({
      applications: [{ at: day(2) }, { at: day(1) }, { at: day(1) }, { at: day(0) }, { at: day(40) }],
      now: NOW,
    });
    expect(out.shape).toBe("burst");
  });

  it("names a long tail when the search spread over months", () => {
    const out = searchPortrait({
      applications: [{ at: day(150) }, { at: day(100) }, { at: day(50) }, { at: day(0) }],
      now: NOW,
    });
    expect(out.shape).toBe("long-tail");
  });

  it("names a steady search when neither extreme holds", () => {
    const out = searchPortrait({
      applications: [{ at: day(20) }, { at: day(14) }, { at: day(7) }, { at: day(0) }],
      now: NOW,
    });
    expect(out.shape).toBe("steady");
  });

  it("treats a search untouched for two months as resting, not shaped", () => {
    // The pattern is history rather than now, and the sentence should say so.
    const out = searchPortrait({
      applications: [{ at: day(90) }, { at: day(80) }, { at: day(70) }, { at: day(61) }],
      now: NOW,
    });
    expect(out.shape).toBe("resting");
  });

  it("calls a single application a fact, not a shape", () => {
    const out = searchPortrait({ applications: [{ at: day(3) }], now: NOW });
    expect(out.shape).toBe("single");
    expect(out.count).toBe(1);
  });

  it("falls back to the count below the shape minimum", () => {
    const out = searchPortrait({ applications: [{ at: day(5) }, { at: day(0) }], now: NOW });
    expect(out.shape).toBe("steady");
    expect(out.count).toBeLessThan(SHAPE_MIN_COUNT);
  });

  it("answers an empty ledger with nothing invented", () => {
    const out = searchPortrait({ applications: [], now: NOW });
    expect(out).toEqual({ count: 0, spanDays: null, busiest: null, shape: "resting" });
  });

  it("ignores a row whose date it cannot read", () => {
    const out = searchPortrait({
      applications: [{ at: "not-a-date" }, { at: day(2) }, { at: day(1) }, { at: day(0) }],
      now: NOW,
    });
    expect(out.count).toBe(3);
  });
});
