import { describe, expect, it } from "vitest";
import { deriveCounsel } from "./admin-counsel";

const labelForStage = (id: string) => `[${id}]`;

const FULL = {
  stats: { users: 40, applications: 0, interviewsPracticed: 1 },
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
    series: {
      applications: [9, 8, 8, 6, 5, 4, 2, 1],
      // The quiet drip: the front door knocked 11 times/wk in the first half, 1/wk now.
      attentionLands: [11, 12, 10, 9, 8, 3, 1, 0],
      attentionDwells: [2, 1, 1, 1, 0, 0, 0, 0],
    },
  },
};

describe("deriveCounsel", () => {
  it("routes every fired rule to a real screen on this install", () => {
    const items = deriveCounsel(FULL, { labelForStage });
    const byId = new Map(items.map((i) => [i.id, i]));
    expect(byId.get("funnel-cliff")?.href).toBe("/applications");
    expect(byId.get("cohort-cliff")?.href).toBe("/growth");
    expect(byId.get("act-rate-zero")?.href).toBe("/");
    expect(byId.get("dwell-rare")?.href).toBe("/");
    expect(byId.get("all-anonymous")?.href).toBe("/register");
    expect(byId.get("attention-collapse")?.href).toBe("/");
    expect(byId.get("attention-soften")?.href).toBe("/");
    expect(byId.get("trend-falling")?.href).toBe("/jobs");
    expect(byId.get("stuck-journey")?.href).toBe("/resumes");
  });

  it("fires the full honest menu when every wire shows the same wall", () => {
    const items = deriveCounsel(FULL, { labelForStage });
    expect(items.map((i) => i.id)).toEqual([
      "funnel-cliff",
      "cohort-cliff",
      "act-rate-zero",
      "dwell-rare",
      "all-anonymous",
      "attention-collapse",
      "attention-soften",
      "trend-falling",
      "stuck-journey",
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

  it("carries the collapse and the soften pair when the front door falls off", () => {
    const items = deriveCounsel({
      trends: {
        weeks: ["w1", "w2", "w3", "w4", "w5", "w6", "w7", "w8"],
        series: {
          // first half avg 10.25, second half avg 2.25 — collapse and soften both fire
          attentionLands: [12, 11, 9, 9, 4, 2, 1, 0],
        },
      },
    });
    expect(items.map((i) => i.id)).toEqual(["attention-collapse", "attention-soften"]);
    const collapse = items.find((i) => i.id === "attention-collapse")!;
    expect(collapse.vars.last).toBe(0);
    // preceding mean = (12+11+9+9+4+2+1)/7 = 48/7 = 6.857 -> rounds to 7
    expect(collapse.vars.base).toBe(7);
    const soften = items.find((i) => i.id === "attention-soften")!;
    expect(soften.vars.recent).toBe(2);
    // first half = [12,11,9,9] avg = 10.25 -> rounds to 10
    expect(soften.vars.base).toBe(10);
  });

  it("stays silent while the window is flat-zero or too short", () => {
    const quiet = deriveCounsel({
      trends: {
        weeks: ["w1", "w2", "w3", "w4", "w5", "w6", "w7", "w8"],
        series: { attentionLands: [0, 0, 0, 0, 0, 0, 0, 0] },
      },
    });
    expect(quiet.find((i) => i.id === "attention-collapse")).toBeUndefined();
    expect(quiet.find((i) => i.id === "attention-soften")).toBeUndefined();

    const short = deriveCounsel({
      trends: { weeks: ["w1", "w2", "w3"], series: { attentionLands: [9, 1, 0] } },
    });
    expect(short.find((i) => i.id === "attention-collapse")).toBeUndefined();
    expect(short.find((i) => i.id === "attention-soften")).toBeUndefined();
  });

  it("collapses only when the latest reading is below 30% of the preceding mean", () => {
    const items = deriveCounsel({
      trends: {
        weeks: ["w1", "w2", "w3", "w4", "w5", "w6", "w7", "w8"],
        // newest = 6 vs mean-of-others = (12+13+15+17+19+18+4)/7 = 98/7 = 14.0 — above the 30% floor
        series: { attentionLands: [12, 13, 15, 17, 19, 18, 4, 6] },
      },
    });
    expect(items.find((i) => i.id === "attention-collapse")).toBeUndefined();
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

  // Epic 422 — the lost-reader behaviours (bounce / aimless) reach the ledger's advice.
  it("names impatient bounces and sends the reader back to the first screen", () => {
    const items = deriveCounsel({
      attention: { landings: 200, bounces: 90, bounceRatePct: 45, dwells: 60, acts: 5,
        signedLandings: 20, anonymousLandings: 180 },
    });
    const bounce = items.find((i) => i.id === "impatient-bounce")!;
    expect(bounce.href).toBe("/");
    expect(bounce.vars).toMatchObject({ bounces: 90, pct: 45, landings: 200 });
  });

  it("names aimless clicking and points the lost ones at the tour", () => {
    const items = deriveCounsel({
      attention: { landings: 200, aimless: 60, bounces: 5, bounceRatePct: 2.5,
        dwells: 60, acts: 5, signedLandings: 20, anonymousLandings: 180 },
    });
    const aimless = items.find((i) => i.id === "aimless-clicking")!;
    expect(aimless.href).toBe("/tour");
    expect(aimless.vars).toMatchObject({ aimless: 60, landings: 200 });
  });

  it("stays silent on the lost-reader rules until the sample is real", () => {
    // bounceRate high but too few bounces; aimless present but a small share — both quiet.
    const items = deriveCounsel({
      attention: { landings: 200, bounces: 4, bounceRatePct: 50, aimless: 5,
        dwells: 60, acts: 5, signedLandings: 20, anonymousLandings: 180 },
    });
    expect(items.find((i) => i.id === "impatient-bounce")).toBeUndefined();
    expect(items.find((i) => i.id === "aimless-clicking")).toBeUndefined();
  });
});
