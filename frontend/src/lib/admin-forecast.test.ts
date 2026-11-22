import { describe, expect, it } from "vitest";

import { deriveLocalMeasures, detectAnomalies, forecast } from "./admin-forecast";

describe("forecast", () => {
  it("projects a clean rising window exactly and names the direction", () => {
    const fc = forecast([10, 12, 14, 16]);
    expect(fc).not.toBeNull();
    expect(fc!.slope).toBeCloseTo(2, 5);
    expect(fc!.direction).toBe("up");
    expect(fc!.next).toEqual([18, 20, 22, 24]);
    expect(fc!.nextTotal).toBe(84);
    expect(fc!.r2).toBeCloseTo(1, 5);
  });

  it("calls a motionless window flat instead of drawing an arrow", () => {
    const fc = forecast([5, 5, 5, 5]);
    expect(fc!.direction).toBe("flat");
    expect(fc!.nextTotal).toBe(20);
  });

  it("clamps a falling projection at zero rather than inventing negative weeks", () => {
    const fc = forecast([10, 6, 2, 0]);
    expect(fc!.direction).toBe("down");
    expect(fc!.next.every((v) => v >= 0)).toBe(true);
  });

  it("refuses a window too short to fit a line", () => {
    expect(forecast([1, 2])).toBeNull();
    expect(forecast(undefined)).toBeNull();
  });
});

describe("detectAnomalies", () => {
  it("flags the newest bucket when it is far outside the prior mean", () => {
    const out = detectAnomalies({ applications: [8, 10, 12, 10, 30] });
    expect(out).toHaveLength(1);
    expect(out[0].key).toBe("applications");
    expect(out[0].direction).toBe("spike");
    expect(out[0].z).toBeGreaterThan(2.5);
  });

  it("stays silent on a steady window and on a flat prior", () => {
    expect(detectAnomalies({ applications: [10, 10, 10, 11] })).toEqual([]);
    expect(detectAnomalies({ applications: [10, 10, 10, 10, 40] })).toEqual([]);
  });
});

describe("deriveLocalMeasures", () => {
  it("names a falling application tide and projects the next four weeks", () => {
    const out = deriveLocalMeasures({
      trends: { series: { applications: [20, 16, 12, 8, 4] } },
    });
    expect(out.map((m) => m.id)).toContain("local-applications-falling");
    const measure = out.find((m) => m.id === "local-applications-falling")!;
    expect(measure.vars).toMatchObject({ first: 20, last: 4, weeks: 5 });
    expect(measure.href).toBe("/jobs");
  });

  it("says nothing when no window is moving down", () => {
    const out = deriveLocalMeasures({
      trends: { series: { applications: [4, 8, 12, 16] } },
    });
    expect(out).toEqual([]);
  });

  it("reports a cold cache only once it has enough calls to mean something", () => {
    expect(
      deriveLocalMeasures({ cache: { totals: { calls: 3, hit_pct: 10 } } }),
    ).toEqual([]);
    const out = deriveLocalMeasures({ cache: { totals: { calls: 40, hit_pct: 12.34 } } });
    expect(out[0].id).toBe("local-cache-cold");
    expect(out[0].vars).toMatchObject({ calls: 40, hit: 12.3 });
  });

  it("caps the ledger at four measures, most urgent first", () => {
    const out = deriveLocalMeasures({
      trends: {
        series: {
          applications: [30, 24, 18, 12, 6],
          attentionLands: [40, 30, 20, 10, 2],
          interviewsPracticed: [12, 9, 6, 3, 1],
          users: [1, 1, 1, 1],
        },
      },
      cache: { totals: { calls: 99, hit_pct: 1 } },
    });
    expect(out).toHaveLength(4);
    expect(out[0].id).toBe("local-applications-falling");
    expect(out[out.length - 1].id).toBe("local-cache-cold");
  });
});
