import { describe, expect, it } from "vitest";
import {
  MAX_COFFEE_SCORE,
  COFFEE_MOMENTS,
  coffeeAnswered,
  coffeeScoreOf,
  coffeeTotalScore,
  coffeeVerdictBand,
  clearCoffeeChat,
  loadCoffeeChat,
  saveCoffeeChat,
} from "./coffee-chat";

function memoryStorage() {
  const map = new Map<string, string>();
  return {
    getItem: (k: string) => map.get(k) ?? null,
    setItem: (k: string, v: string) => void map.set(k, v),
    removeItem: (k: string) => void map.delete(k),
  } as unknown as Storage;
}

describe("coffee moments", () => {
  it("three moments, three replies each, nine points on the table", () => {
    expect(COFFEE_MOMENTS).toHaveLength(3);
    for (const moment of COFFEE_MOMENTS) {
      expect(moment.replies).toHaveLength(3);
    }
    expect(MAX_COFFEE_SCORE).toBe(9);
    expect(coffeeScoreOf("ask", "burden")).toBe(0);
    expect(coffeeScoreOf("ask", "generic")).toBe(1);
    expect(coffeeScoreOf("ask", "specific")).toBe(3);
    expect(coffeeScoreOf("middle", "nothing")).toBe(0);
    expect(coffeeScoreOf("middle", "recap")).toBe(1);
    expect(coffeeScoreOf("middle", "lead")).toBe(3);
    expect(coffeeScoreOf("close", "thanks")).toBe(0);
    expect(coffeeScoreOf("close", "loop")).toBe(1);
    expect(coffeeScoreOf("close", "forward")).toBe(3);
    expect(coffeeScoreOf("close", "missing")).toBe(0);
  });

  it("is unanswered until every moment is played", () => {
    expect(coffeeAnswered({ scores: {}, sentence: "" })).toBe(false);
    expect(
      coffeeAnswered({ scores: { ask: "specific", middle: "lead", close: "forward" }, sentence: "" })
    ).toBe(true);
    expect(
      coffeeAnswered({ scores: { ask: "specific" }, sentence: "" })
    ).toBe(false);
  });

  it("sums only the moments it knows", () => {
    expect(coffeeTotalScore({ scores: { ask: "specific", middle: "lead" }, sentence: "" })).toBe(6);
    // A stray key from a foreign file cannot leak in: loadCoffeeChat drops it.
    const storage = memoryStorage();
    storage.setItem(
      "careeros.coffeechat.v1",
      JSON.stringify({ scores: { ask: "specific", bogus: "specific" }, sentence: "s" })
    );
    const loaded = loadCoffeeChat(storage);
    expect(coffeeTotalScore(loaded)).toBe(3);
  });

  it("bands the nine points honestly", () => {
    expect(coffeeVerdictBand(0)).toBe("none");
    expect(coffeeVerdictBand(2)).toBe("weak");
    expect(coffeeVerdictBand(5)).toBe("solid");
    expect(coffeeVerdictBand(8)).toBe("strong");
    expect(coffeeVerdictBand(9)).toBe("masterful");
  });
});

describe("coffee-chat storage round trip", () => {
  it("saves, survives, and clears", () => {
    const storage = memoryStorage();
    saveCoffeeChat({ scores: { ask: "specific" }, sentence: "One coffee, fifteen minutes." }, storage);
    expect(loadCoffeeChat(storage).scores.ask).toBe("specific");
    expect(loadCoffeeChat(storage).sentence).toBe("One coffee, fifteen minutes.");
    clearCoffeeChat(storage);
    expect(loadCoffeeChat(storage).scores).toEqual({});
  });

  it("refuses a blob that is not JSON", () => {
    const storage = memoryStorage();
    storage.setItem("careeros.coffeechat.v1", "nope {");
    expect(loadCoffeeChat(storage)).toEqual({ scores: {}, sentence: "" });
  });

  it("refuses a blob whose sentence is not a string and caps a long one", () => {
    const storage = memoryStorage();
    storage.setItem(
      "careeros.coffeechat.v1",
      JSON.stringify({ scores: {}, sentence: "x".repeat(9000) })
    );
    const loaded = loadCoffeeChat(storage);
    expect(loaded.sentence).toHaveLength(2000);
  });

  it("refuses score entries for unknown moments or replies", () => {
    const storage = memoryStorage();
    storage.setItem(
      "careeros.coffeechat.v1",
      JSON.stringify({ scores: { ask: "bogus", close: "forward" }, sentence: 42 })
    );
    const loaded = loadCoffeeChat(storage);
    expect(loaded.scores).toEqual({ close: "forward" });
    expect(loaded.sentence).toBe("");
  });
});
