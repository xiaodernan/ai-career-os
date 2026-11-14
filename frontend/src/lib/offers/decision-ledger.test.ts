import { describe, expect, it } from "vitest";
import {
  LEDGER_MAX_CRITERIA,
  addCriterion,
  clearLedger,
  computeLedger,
  ledgerIsDirty,
  loadLedger,
  removeCriterion,
  saveLedger,
  setScore,
  setWeight,
  starterLedger,
  type LedgerState,
} from "./decision-ledger";

function memoryStorage() {
  const map = new Map<string, string>();
  return {
    getItem: (key: string) => map.get(key) ?? null,
    setItem: (key: string, value: string) => void map.set(key, value),
    removeItem: (key: string) => void map.delete(key),
  };
}

describe("starterLedger", () => {
  it("ships six starters with a sane default weight order", () => {
    const state = starterLedger();
    expect(state.criteria.map((c) => c.id)).toEqual([
      "comp",
      "growth",
      "team",
      "mission",
      "location",
      "stability",
    ]);
    expect(state.criteria.reduce((sum, c) => sum + c.weight, 0)).toBeGreaterThan(0);
    expect(state.criteria.every((c) => c.weight >= 0 && c.weight <= 5)).toBe(true);
  });
});

describe("loadLedger / saveLedger round trip", () => {
  it("persists criteria, weights and scores, and reads them back", () => {
    const storage = memoryStorage();
    let state = starterLedger();
    state = setWeight(state, "mission", 5);
    state = setScore(state, "offer-1", "comp", 9);
    state = setScore(state, "offer-2", "comp", 4);
    saveLedger(state, storage);
    const loaded = loadLedger(storage);
    expect(loaded.criteria.find((c) => c.id === "mission")?.weight).toBe(5);
    expect(loaded.scores["offer-1"].comp).toBe(9);
  });

  it("returns the starter when storage holds garbage", () => {
    const storage = memoryStorage();
    storage.setItem("careeros.ledger.v1", "not json {");
    expect(loadLedger(storage).criteria.map((c) => c.id)).toEqual([
      "comp",
      "growth",
      "team",
      "mission",
      "location",
      "stability",
    ]);
  });

  it("clamps out-of-range weights and scores rather than trusting them", () => {
    const storage = memoryStorage();
    storage.setItem(
      "careeros.ledger.v1",
      JSON.stringify({
        criteria: [{ id: "comp", custom: false, label: "", weight: 99 }],
        scores: { "offer-1": { comp: 42, bogus: 7 } },
      }),
    );
    const loaded = loadLedger(storage);
    expect(loaded.criteria[0].weight).toBe(5);
    expect(loaded.scores["offer-1"]).toEqual({ comp: 10 });
  });

  it("clearLedger removes the persisted state", () => {
    const storage = memoryStorage();
    saveLedger(setScore(starterLedger(), "offer-1", "comp", 8), storage);
    clearLedger(storage);
    expect(storage.getItem("careeros.ledger.v1")).toBeNull();
  });
});

describe("addCriterion / removeCriterion", () => {
  it("adds a custom criterion with the starter default weight", () => {
    const next = addCriterion(starterLedger(), "Space to do my own work");
    expect(next).not.toBeNull();
    const added = next!.criteria[next!.criteria.length - 1];
    expect(added.custom).toBe(true);
    expect(added.label).toBe("Space to do my own work");
    expect(added.weight).toBe(3);
  });

  it("refuses blank labels and refuses beyond the cap", () => {
    expect(addCriterion(starterLedger(), "   ")).toBeNull();
    let state = starterLedger();
    for (let i = state.criteria.length; i < LEDGER_MAX_CRITERIA; i += 1) {
      state = addCriterion(state, `Criterion ${i}`)!;
    }
    expect(state.criteria.length).toBe(LEDGER_MAX_CRITERIA);
    expect(addCriterion(state, "one more")).toBeNull();
  });

  it("removing a criterion drops its scores everywhere", () => {
    let state = starterLedger();
    state = setScore(state, "offer-1", "comp", 9);
    state = setScore(state, "offer-1", "team", 7);
    state = removeCriterion(state, "comp");
    expect(state.criteria.map((c) => c.id)).not.toContain("comp");
    expect(state.scores["offer-1"]).toEqual({ team: 7 });
  });
});

describe("setScore", () => {
  it("records a zero as a real score", () => {
    const state = setScore(starterLedger(), "offer-1", "comp", 0);
    expect(state.scores["offer-1"].comp).toBe(0);
  });

  it("clears the cell on blank input and drops empty offer entries", () => {
    let state = setScore(starterLedger(), "offer-1", "comp", 9);
    state = setScore(state, "offer-1", "comp", "");
    expect(state.scores["offer-1"]).toBeUndefined();
  });
});

describe("computeLedger", () => {
  it("weights scores, caps at max, and crowns a single leader", () => {
    let state: LedgerState = starterLedger();
    state = setScore(state, "offer-a", "comp", 10); // 5 * 10 = 50
    state = setScore(state, "offer-a", "growth", 4); // 4 * 4 = 16
    state = setScore(state, "offer-b", "comp", 6); // 30
    const result = computeLedger(["offer-a", "offer-b"], state);
    const a = result.rows.find((r) => r.offerId === "offer-a")!;
    const b = result.rows.find((r) => r.offerId === "offer-b")!;
    expect(a.total).toBe(66);
    expect(b.total).toBe(30);
    expect(a.max).toBe(state.criteria.reduce((sum, c) => sum + c.weight * 10, 0));
    expect(result.leaderIds).toEqual(["offer-a"]);
  });

  it("reports a genuine tie as more than one leader", () => {
    let state = starterLedger();
    state = setScore(state, "offer-a", "comp", 10);
    state = setScore(state, "offer-b", "comp", 10);
    const result = computeLedger(["offer-a", "offer-b"], state);
    expect(result.leaderIds.sort()).toEqual(["offer-a", "offer-b"]);
  });

  it("a zero-weight criterion contributes nothing to totals", () => {
    let state = starterLedger();
    state = setWeight(state, "comp", 0);
    state = setScore(state, "offer-a", "comp", 10);
    const result = computeLedger(["offer-a"], state);
    expect(result.rows[0].total).toBe(0);
    // A crown only exists when the weights separate something: all zeros is not a signal.
    expect(result.leaderIds).toEqual([]);
  });

  it("recorded all-zero scores crown nobody — nothing separates the rows yet", () => {
    let state = starterLedger();
    state = setScore(state, "offer-a", "comp", 0);
    state = setScore(state, "offer-b", "comp", 0);
    expect(computeLedger(["offer-a", "offer-b"], state).leaderIds).toEqual([]);
  });

  it("an offer with no recorded scores never shares the crown", () => {
    let state = starterLedger();
    state = setScore(state, "offer-a", "comp", 5); // 25 > 0
    const result = computeLedger(["offer-a", "offer-b"], state);
    expect(result.leaderIds).toEqual(["offer-a"]);
  });

  it("nothing scored means nothing crowned", () => {
    expect(computeLedger(["offer-a"], starterLedger()).leaderIds).toEqual([]);
  });

  it("removing every criterion falls back to the starter ledger", () => {
    let state = starterLedger();
    for (const c of [...state.criteria]) {
      state = removeCriterion(state, c.id);
    }
    expect(state.criteria.map((c) => c.id)).toEqual([
      "comp",
      "growth",
      "team",
      "mission",
      "location",
      "stability",
    ]);
  });
});

describe("ledgerIsDirty", () => {
  it("is false for a pristine starter ledger", () => {
    expect(ledgerIsDirty(starterLedger())).toBe(false);
  });

  it("is true once the reader scores anything, edits a weight, or adds a criterion", () => {
    expect(ledgerIsDirty(setScore(starterLedger(), "offer-a", "comp", 1))).toBe(true);
    expect(ledgerIsDirty(setWeight(starterLedger(), "comp", 4))).toBe(true);
    expect(ledgerIsDirty(addCriterion(starterLedger(), "My own")!)).toBe(true);
  });
});
