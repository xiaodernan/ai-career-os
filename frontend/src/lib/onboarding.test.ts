import { describe, expect, it } from "vitest";
import { markQuickStartSeen, needsQuickStart, resetQuickStart } from "./onboarding";

function fakeStorage(): Storage {
  const data = new Map<string, string>();
  return {
    get length() { return data.size; },
    clear: () => data.clear(),
    getItem: (k: string) => data.get(k) ?? null,
    key: (i: number) => [...data.keys()][i] ?? null,
    removeItem: (k: string) => { data.delete(k); },
    setItem: (k: string, v: string) => { data.set(k, v); },
  } as Storage;
}

describe("first-run quick start state", () => {
  it("is needed on a fresh browser", () => {
    expect(needsQuickStart(fakeStorage())).toBe(true);
  });

  it("persists seen across reads", () => {
    const s = fakeStorage();
    markQuickStartSeen(s);
    expect(needsQuickStart(s)).toBe(false);
    expect(needsQuickStart(s)).toBe(false);
  });

  it("can be replayed by clearing the flag", () => {
    const s = fakeStorage();
    markQuickStartSeen(s);
    resetQuickStart(s);
    expect(needsQuickStart(s)).toBe(true);
  });

  it("shows the guide when storage is unavailable", () => {
    expect(needsQuickStart(null)).toBe(true);
    expect(() => markQuickStartSeen(null)).not.toThrow();
  });
});
