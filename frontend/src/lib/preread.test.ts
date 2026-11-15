import { describe, expect, it } from "vitest";

import {
  LENS_IDS,
  MAX_TOTAL,
  PREREAD_PREFIX,
  READY_TOTAL,
  blankState,
  levelTotal,
  parsePreread,
  readPreread,
  synthesisLenses,
  readyForSynthesis,
  writePreread,
  type PrereadState,
} from "./preread";

function fakeStorage(seed: Record<string, string> = {}) {
  const map = new Map<string, string>(Object.entries(seed));
  return {
    getItem: (k: string) => map.get(k) ?? null,
    setItem: (k: string, v: string) => void map.set(k, v),
    removeItem: (k: string) => void map.delete(k),
    seed,
  };
}

const FULL: PrereadState = {
  notes: {
    money: "Take-rate on the marketplace; if liquidity stays healthy, the take holds.",
    role: "A two-person platform team, reporting to the VP of Product; own the intake pipeline alone by month two.",
    year: "Launched the AI copilot in Q2, slipped the mobile app to Q4, and a new CPO joined in June.",
    proof: "They will smell the gap between my SRE months and their infra bar fastest.",
    bet: "This is the only room where I could hold both the marketplace and the platform hat at once.",
  },
  levels: { money: 2, role: 2, year: 2, proof: 1, bet: 2 },
  keptAt: "2026-11-16T00:00:00.000Z",
};

describe("parsePreread", () => {
  it("reads garbage as a blank kit, never an exception", () => {
    expect(parsePreread("not json")).toEqual(blankState());
    expect(parsePreread("[array]")).toEqual(blankState());
    expect(parsePreread(null)).toEqual(blankState());
    expect(parsePreread('{"levels":{"money":7,"role":-1}}').levels.money).toBe(0);
  });

  it("keeps unknown levels at 0 and keeps notes as strings", () => {
    const parsed = parsePreread(JSON.stringify({ notes: { money: 42 }, levels: { money: 2 } }));
    expect(parsed.notes.money).toBe("");
    expect(parsed.levels.money).toBe(2);
  });
});

describe("storage round trip", () => {
  it("returns to exactly what was written", () => {
    const storage = fakeStorage();
    writePreread("co-1", FULL, storage);
    expect(readPreread("co-1", storage)).toEqual(FULL);
    expect(storage.getItem(`${PREREAD_PREFIX}co-1`)).toContain("2026-11-16");
  });

  it("reads blank for an unknown company", () => {
    expect(readPreread("never-seen", fakeStorage())).toEqual(blankState());
  });
});

describe("levelTotal / readyForSynthesis", () => {
  it("sums the five levels and caps the scale at two each", () => {
    expect(levelTotal(blankState())).toBe(0);
    expect(levelTotal(FULL)).toBe(9);
    expect(MAX_TOTAL).toBe(10);
  });

  it("gates synthesis until the kit is written through", () => {
    const low: PrereadState = { ...FULL, levels: { money: 2, role: 2, year: 2, proof: 1, bet: 0 } };
    expect(levelTotal(low)).toBe(7);
    expect(readyForSynthesis(low)).toBe(false);
    expect(readyForSynthesis(FULL)).toBe(true);
  });
});

describe("synthesisLenses", () => {
  it("prefers context lenses, in order, and skips empty voices", () => {
    expect(synthesisLenses(FULL)).toEqual(["year", "role"]);
    const noWeather = { ...FULL, notes: { ...FULL.notes, year: "", role: "" } };
    expect(synthesisLenses(noWeather)).toEqual(["money", "proof"]);
  });

  it("refuses a lens whose words are too thin to quote", () => {
    const thin = { notes: { ...blankState().notes, year: "short" } };
    expect(synthesisLenses(thin)).toEqual([]);
  });

  it("covers every known lens id", () => {
    expect(LENS_IDS).toHaveLength(5);
    expect(new Set(LENS_IDS).size).toBe(5);
  });
});

describe("READY_TOTAL", () => {
  it("is reachable without marking every lens twice", () => {
    expect(READY_TOTAL).toBe(8);
    expect(READY_TOTAL).toBeLessThanOrEqual(MAX_TOTAL);
  });
});
