import { describe, expect, it } from "vitest";

import {
  SLOT_COUNT,
  blankState,
  filledSlots,
  isSealed,
  parseNearMiss,
  readNearMiss,
  writeNearMiss,
  NEARMISS_PREFIX,
} from "./nearmiss";

function fakeStorage(seed: Record<string, string> = {}) {
  const map = new Map<string, string>(Object.entries(seed));
  return {
    getItem: (k: string) => map.get(k) ?? null,
    setItem: (k: string, v: string) => void map.set(k, v),
    removeItem: (k: string) => void map.delete(k),
    map,
  };
}

const FULL = {
  role: "Platform engineer",
  company: "Lunar Works",
  again: true as const,
  learned: "Competing world-class is not about knowing every technology; it is about one sentence per signal.",
  changed: "I stopped rehearsing scripted stories and started rehearsing 30 authentic minutes.",
  keptAt: "2026-11-16T00:00:00.000Z",
};

describe("parseNearMiss", () => {
  it("reads corruption as a blank shelf", () => {
    expect(parseNearMiss("garbage")).toEqual(blankState());
    expect(parseNearMiss("[1,2]")).toEqual(blankState());
    expect(parseNearMiss(null)).toEqual(blankState());
  });

  it("clamps every field to a bound", () => {
    const long = "x".repeat(5000);
    const parsed = parseNearMiss(JSON.stringify({ role: long }));
    expect(parsed.role.length).toBe(400);
  });
});

describe("storage round trip", () => {
  it("preserves exactly what was written", () => {
    const storage = fakeStorage();
    writeNearMiss(FULL, storage);
    expect(readNearMiss(storage)).toEqual(FULL);
    expect(storage.map.get(`${NEARMISS_PREFIX}v1`)).toContain("2026-11-16");
  });
});

describe("completion counting", () => {
  it("starts at zero and fills five slots", () => {
    expect(filledSlots(blankState())).toHaveLength(0);
    expect(filledSlots(FULL)).toHaveLength(SLOT_COUNT);
  });

  it("counts the ask-again toggle as a filled slot only when chosen", () => {
    const half = { ...FULL, again: null };
    expect(filledSlots(half)).toHaveLength(4);
  });
});

describe("isSealed", () => {
  it("requires the role and the lesson, nothing else", () => {
    expect(isSealed(blankState())).toBe(false);
    expect(isSealed({ ...blankState(), role: "S", learned: FULL.learned })).toBe(false);
    expect(isSealed({ ...blankState(), role: FULL.role, learned: "eight chars please" })).toBe(true);
  });
});
