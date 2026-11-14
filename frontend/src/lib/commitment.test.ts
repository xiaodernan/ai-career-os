import { describe, expect, it } from "vitest";
import {
  COMMITMENT_MAX_LENGTH,
  clearCommitment,
  isoWeekKey,
  loadCommitment,
  saveCommitment,
} from "./commitment";

function memoryStorage() {
  const map = new Map<string, string>();
  return {
    getItem: (k: string) => map.get(k) ?? null,
    setItem: (k: string, v: string) => void map.set(k, v),
    removeItem: (k: string) => void map.delete(k),
  } as unknown as Storage;
}

describe("isoWeekKey", () => {
  it("computes ISO week labels with year edges right", () => {
    expect(isoWeekKey(new Date(Date.UTC(2026, 10, 16)))).toBe("2026-W47");  // Nov 16 2026 (Mon)
    expect(isoWeekKey(new Date(Date.UTC(2026, 0, 1)))).toBe("2026-W01");    // Jan 1 2026 (Thu)
    expect(isoWeekKey(new Date(Date.UTC(2027, 0, 1)))).toBe("2026-W53");    // Jan 1 2027 (Fri) — still 2026's week 53
    expect(isoWeekKey(new Date(Date.UTC(2026, 11, 31)))).toBe("2026-W53");  // Dec 31 2026 (Thu)
  });

  it("a Sunday belongs to the week it just closed", () => {
    expect(isoWeekKey(new Date(Date.UTC(2026, 10, 22)))).toBe(isoWeekKey(new Date(Date.UTC(2026, 10, 16))));
  });
});

describe("commitment round trip", () => {
  it("saves, trims at 280 chars, and forgets", () => {
    const storage = memoryStorage();
    saveCommitment("I will ask for the range before Friday.", storage);
    expect(loadCommitment(storage).text).toBe("I will ask for the range before Friday.");
    saveCommitment("x".repeat(400), storage);
    expect(loadCommitment(storage).text).toHaveLength(COMMITMENT_MAX_LENGTH);
    clearCommitment(storage);
    expect(loadCommitment(storage).text).toBe("");
  });

  it("returns the empty commitment when the blob is not JSON", () => {
    const storage = memoryStorage();
    storage.setItem(`${"careeros.commitment."}${isoWeekKey()}`, "nope {");
    expect(loadCommitment(storage).text).toBe("");
  });

  it("rejects a blob with no text field", () => {
    const storage = memoryStorage();
    storage.setItem(`${"careeros.commitment."}${isoWeekKey()}`, JSON.stringify({ other: 1 }));
    expect(loadCommitment(storage).text).toBe("");
  });
});
