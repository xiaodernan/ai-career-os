import { describe, expect, it } from "vitest";
import { deriveCounsel } from "./admin-counsel";

const labelForStage = (id: string) => `[${id}]`;

const FULL = {
  stats: { users: 40, applications: 3, interviewsPracticed: 1 },
  funnel: {
    stages: [
      { id: "registered", readers: 100 },
      { id: "uploaded", readers: 60 },
      { id: "matched", readers: 12 }, // steepest: uploaded -> matched, 80% drop
      { id: "interviewed", readers: 6 },
    ],
  },
  cohort: {
    cohort: Array.from({ length: 6 }, (_, i) => ({
      week: `2026-10-0${i + 1}`,
      registered: 10,
      active: i < 2 ? 9 : 2, // newest four weeks: 40 registered, 14 active -> 35%
    })),
  },
  attention: {
    landings: 200,
    dwells: 10, // 5% — below the 10% floor
    acts: 0,
    signedLandings: 0,
    anonymousLandings: 200,
  },
  trends: {
    weeks: ["2026-01-01", "2026-01-08", "2026-01-15", "2026-01-22", "2026-01-29", "2026-02-05", "2026-02-12", "2026-02-19"],
    series: { applications: [9, 8, 8, 6, 5, 4, 2, 1] },
  },
};

describe("deriveCounsel", () => {
  it("fires the full honest menu when every wire shows the same wall", () => {
    const items = deriveCounsel(FULL, { labelForStage });
    expect(items.map((i) => i.id)).toEqual([
      "funnel-cliff",
      "cohort-cliff",
      "act-rate-zero",
      "dwell-rare",
      "all-anonymous",
      "trend-falling",
    ]);
  });

  it("names the stages the label lookup carries, and the drop that fired it", () => {
    const [funnel] = deriveCounsel(FULL, { labelForStage });
    expect(funnel.vars.from).toBe("[uploaded]");
    expect(funnel.vars.to).toBe("[matched]");
    expect(funnel.vars.fromCount).toBe(60);
    expect(funnel.vars.toCount).toBe(12);
    expect(funnel.vars.dropPct).toBe(80);
  });

  it("keeps the attention bodies in the reader's own numbers", () => {
    const items = deriveCounsel(FULL);
    const dwell = items.find((i) => i.id === "dwell-rare")!;
    expect(dwell.vars.pct).toBe(5);
    expect(dwell.vars.dwells).toBe(10);
    const anon = items.find((i) => i.id === "all-anonymous")!;
    expect(anon.vars.landings).toBe(200);
  });

  it("stays silent where the wires have nothing to say", () => {
    // A healthy wall: high retention, strong funnel, real acts, falling nothing.
    const calm = deriveCounsel({
      stats: { users: 30, applications: 12 },
      funnel: {
        stages: [
          { id: "registered", readers: 100 },
          { id: "uploaded", readers: 80 },
          { id: "matched", readers: 70 },
        ],
      },
      cohort: { cohort: [{ week: "2026-10-06", registered: 10, active: 9 }] },
      attention: { landings: 300, dwells: 90, acts: 7, signedLandings: 120, anonymousLandings: 180 },
      trends: {
        series: { applications: [1, 2, 3, 4, 5, 6, 7, 8] },
      },
    });
    expect(calm).toEqual([]);
  });

  it("reads nothing, invents nothing, when the wires have not landed at all", () => {
    expect(deriveCounsel({})).toEqual([]);
    expect(deriveCounsel({ attention: {}, funnel: null, cohort: undefined })).toEqual([]);
  });

  it("does not mistake an empty applications window for a falling tide", () => {
    const items = deriveCounsel({ trends: { series: { applications: [0, 0, 0, 0, 0, 0, 0, 0] } } });
    expect(items.find((i) => i.id === "trend-falling")).toBeUndefined();
  });

  it("fires stuck-journey only past a signup with zero applications", () => {
    expect(deriveCounsel({ stats: { users: 0, applications: 0 } })).toEqual([]);
    const [item] = deriveCounsel({ stats: { users: 25, applications: 0 } });
    expect(item.id).toBe("stuck-journey");
    expect(item.vars.users).toBe(25);
  });

  it("ignores tiny attention samples rather than dressing noise as insight", () => {
    const items = deriveCounsel({ attention: { landings: 5, dwells: 0, acts: 0, signedLandings: 0, anonymousLandings: 5 } });
    expect(items).toEqual([]);
  });
});
