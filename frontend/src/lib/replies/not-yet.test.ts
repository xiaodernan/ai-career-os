import { describe, expect, it } from "vitest";
import {
  NOT_YET_DOORS,
  NOT_YET_MAX_LENGTH,
  clearNotYet,
  loadNotYet,
  saveNotYet,
} from "./not-yet";

function memoryStorage() {
  const map = new Map<string, string>();
  return {
    getItem: (k: string) => map.get(k) ?? null,
    setItem: (k: string, v: string) => void map.set(k, v),
    removeItem: (k: string) => void map.delete(k),
  } as unknown as Storage;
}

describe("the not-yet letter", () => {
  it("three doors, the three shapes recruiters actually write", () => {
    expect(NOT_YET_DOORS.map((d) => d.id)).toEqual(["calibrate", "hold", "impress"]);
  });

  it("saves, trims at the cap, and forgets", () => {
    const storage = memoryStorage();
    saveNotYet("They wrote 'impress' — I will find out about the tiebreaker.", storage);
    expect(loadNotYet(storage).sentence).toBe("They wrote 'impress' — I will find out about the tiebreaker.");
    saveNotYet("x".repeat(3000), storage);
    expect(loadNotYet(storage).sentence).toHaveLength(NOT_YET_MAX_LENGTH);
    clearNotYet(storage);
    expect(loadNotYet(storage).sentence).toBe("");
  });

  it("refuses a blob that is not JSON, and drops a non-string sentence", () => {
    const storage = memoryStorage();
    storage.setItem("careeros.notyet.v1", "nope {");
    expect(loadNotYet(storage).sentence).toBe("");
    storage.setItem("careeros.notyet.v1", JSON.stringify({ sentence: 42 }));
    expect(loadNotYet(storage).sentence).toBe("");
  });
});
