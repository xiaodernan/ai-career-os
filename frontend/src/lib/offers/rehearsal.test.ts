import { describe, expect, it } from "vitest";
import {
  MAX_REHEARSAL_SCORE,
  REHEARSAL_PUSHES,
  answered,
  clearRehearsal,
  loadRehearsal,
  saveRehearsal,
  totalScore,
  verdictBand,
  type RehearsalState,
} from "./rehearsal";

function memoryStorage() {
  const map = new Map<string, string>();
  return {
    getItem: (k: string) => map.get(k) ?? null,
    setItem: (k: string, v: string) => void map.set(k, v),
    removeItem: (k: string) => void map.delete(k),
  };
}

describe("REHEARSAL_PUSHES", () => {
  it("three pushes, three replies each, scored 0/1/2/3 honestly", () => {
    expect(REHEARSAL_PUSHES).toHaveLength(3);
    for (const push of REHEARSAL_PUSHES) {
      expect(push.replies).toHaveLength(3);
      const scores = push.replies.map((r) => r.score);
      expect(new Set(scores).size).toBe(scores.length);
    }
    expect(REHEARSAL_PUSHES.map((p) => p.id)).toEqual(["band", "silence", "anchor"]);
  });
});

describe("scoreOf and totalScore", () => {
  it("sums the reader's picks honestly", () => {
    const state: RehearsalState = {
      scores: { band: "hold", silence: "clock", anchor: "evidence" },
      sentence: "",
    };
    expect(totalScore(state)).toBe(9);
    expect(totalScore({ scores: { band: "concede" }, sentence: "" })).toBe(0);
  });

  it("ignores scores for pushes the reader never saw", () => {
    expect(totalScore({ scores: { moonshot: "spot-on" }, sentence: "" })).toBe(0);
  });
});

describe("answered", () => {
  it("is false with fewer than three picks and true with exactly three", () => {
    expect(answered({ scores: { band: "open" }, sentence: "" })).toBe(false);
    expect(
      answered({ scores: { band: "open", silence: "clock", anchor: "gap" }, sentence: "" })
    ).toBe(true);
  });
});

describe("verdictBand", () => {
  it("maps 0/1/3/6/9 honest honor ribbons", () => {
    expect(verdictBand(0)).toBe("none");
    expect(verdictBand(2)).toBe("weak");
    expect(verdictBand(5)).toBe("solid");
    expect(verdictBand(8)).toBe("strong");
    expect(verdictBand(9)).toBe("masterful");
    expect(verdictBand(6)).toBe("strong");
  });
});

describe("localStorage round trip", () => {
  it("saves and restores what the reader wrote", () => {
    const storage = memoryStorage() as unknown as Storage;
    const state: RehearsalState = {
      scores: { silence: "clock", anchor: "gap" },
      sentence: "I'd love to walk in with a number.",
    };
    saveRehearsal(state, storage);
    expect(loadRehearsal(storage)).toEqual(state);
  });

  it("returns the empty state when the blob is not JSON", () => {
    const storage = memoryStorage() as unknown as Storage;
    storage.setItem("careeros.rehearsal.v1", "not json {");
    expect(loadRehearsal(storage)).toEqual({ scores: {}, sentence: "" });
  });

  it("drops reply ids that no longer exist in the graph", () => {
    const storage = memoryStorage() as unknown as Storage;
    storage.setItem(
      "careeros.rehearsal.v1",
      JSON.stringify({ scores: { band: "hold", silence: "deleted-reply" }, sentence: "ok" })
    );
    expect(loadRehearsal(storage)).toEqual({ scores: { band: "hold" }, sentence: "ok" });
  });

  it("clearRehearsal forgets everything", () => {
    const storage = memoryStorage() as unknown as Storage;
    saveRehearsal(
      { scores: { band: "open" }, sentence: "an ask" } as RehearsalState,
      storage
    );
    clearRehearsal(storage);
    expect(loadRehearsal(storage)).toEqual({ scores: {}, sentence: "" });
  });
});

describe("MAX_REHEARSAL_SCORE", () => {
  it("is three pushes times three points", () => {
    expect(MAX_REHEARSAL_SCORE).toBe(9);
  });
});
