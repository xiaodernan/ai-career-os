import { describe, expect, it } from "vitest";
import {
  clearDebrief,
  debriefIsEmpty,
  loadDebrief,
  saveDebrief,
} from "./debrief";

function memoryStorage() {
  const map = new Map<string, string>();
  return {
    getItem: (key: string) => map.get(key) ?? null,
    setItem: (key: string, value: string) => void map.set(key, value),
    removeItem: (key: string) => void map.delete(key),
  };
}

describe("loadDebrief / saveDebrief", () => {
  it("round-trips the two fields per session id", () => {
    const storage = memoryStorage();
    saveDebrief("s-1", { whatHappened: "I rambled on Q2.", differently: "Name the result first." }, storage);
    expect(loadDebrief("s-1", storage)).toEqual({
      whatHappened: "I rambled on Q2.",
      differently: "Name the result first.",
    });
    expect(loadDebrief("s-2", storage)).toEqual({ whatHappened: "", differently: "" });
  });

  it("returns empty state when storage holds garbage or nothing", () => {
    const storage = memoryStorage();
    storage.setItem("careeros.debrief.s-1", "not json {");
    expect(loadDebrief("s-1", storage)).toEqual({ whatHappened: "", differently: "" });
    expect(loadDebrief("missing", storage)).toEqual({ whatHappened: "", differently: "" });
  });

  it("clearDebrief forgets only that session", () => {
    const storage = memoryStorage();
    saveDebrief("s-1", { whatHappened: "a", differently: "b" }, storage);
    saveDebrief("s-2", { whatHappened: "c", differently: "d" }, storage);
    clearDebrief("s-1", storage);
    expect(loadDebrief("s-1", storage).whatHappened).toBe("");
    expect(loadDebrief("s-2", storage).whatHappened).toBe("c");
  });

  it("ignores absurd payloads and clamps to the field cap", () => {
    const storage = memoryStorage();
    storage.setItem(
      "careeros.debrief.s-1",
      JSON.stringify({ whatHappened: 42, differently: "x".repeat(10_000) }),
    );
    const loaded = loadDebrief("s-1", storage);
    expect(loaded.whatHappened).toBe("");
    expect(loaded.differently).toHaveLength(4000);
  });
});

describe("debriefIsEmpty", () => {
  it("is true only when both fields are blank or whitespace", () => {
    expect(debriefIsEmpty({ whatHappened: "", differently: "  \n " })).toBe(true);
    expect(debriefIsEmpty({ whatHappened: "a", differently: "" })).toBe(false);
    expect(debriefIsEmpty({ whatHappened: "", differently: "b" })).toBe(false);
  });
});
