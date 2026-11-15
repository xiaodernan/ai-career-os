import { describe, expect, it } from "vitest";

import { seriesTotal, sparkline } from "./admin-trend";

describe("sparkline", () => {
  it("returns null for no points — an empty chart is nothing, not a flat mystery", () => {
    expect(sparkline([])).toBeNull();
  });

  it("draws oldest on the left and the newest point on the right edge", () => {
    const out = sparkline([1, 2, 3, 4], 120, 36, 3);
    expect(out).not.toBeNull();
    const coords = out!.points.split(" ").map((pair) => pair.split(",").map(Number));
    expect(coords[0][0]).toBeCloseTo(3, 1);
    expect(coords[coords.length - 1][0]).toBeCloseTo(117, 1);
    // monotone rise: each y is higher on screen (smaller) than the last
    for (let i = 1; i < coords.length; i++) {
      expect(coords[i][1]).toBeLessThan(coords[i - 1][1]);
    }
    expect(out!.last).toEqual({ x: coords.at(-1)![0], y: coords.at(-1)![1] });
  });

  it("pins a same-height series to the baseline, not mid-air", () => {
    const out = sparkline([0, 0, 0], 120, 36, 3)!;
    expect(out.points).toBe("3,33 60,33 117,33");
    expect(out.peak).toBe(-1);
  });

  it("finds the peak at the first highest value", () => {
    expect(sparkline([5, 9, 9, 2])?.peak).toBe(1);
    expect(sparkline([0, 0, 3])?.peak).toBe(2);
  });

  it("clamps a rogue negative to the baseline rather than drawing off-canvas", () => {
    const out = sparkline([-5, 3], 120, 36, 3)!;
    const coords = out.points.split(" ").map((pair) => pair.split(",").map(Number));
    expect(coords[0][1]).toBeLessThanOrEqual(33);
    expect(coords[0][1]).toBeGreaterThanOrEqual(3);
    expect(coords[1][1]).toBeLessThan(coords[0][1]);
  });

  it("a single value draws one point at the left edge without dividing by zero", () => {
    const out = sparkline([7], 120, 36, 3)!;
    expect(out.points).toBe("3,3");
    expect(out.last).toEqual({ x: 3, y: 3 });
  });
});

describe("seriesTotal", () => {
  it("sums the window and reads an empty one as zero", () => {
    expect(seriesTotal([3, 4, 5])).toBe(12);
    expect(seriesTotal([])).toBe(0);
  });
});
