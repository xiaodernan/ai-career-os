import { describe, expect, it } from "vitest";
import {
  FIRST_WEEK_SCENES,
  MAX_FIRST_WEEK_SCORE,
  clearFirstWeek,
  firstWeekAnswered,
  firstWeekPoints,
  firstWeekTotal,
  firstWeekVerdict,
  loadFirstWeek,
  saveFirstWeek,
} from "./first-week";

function memoryStorage() {
  const map = new Map<string, string>();
  return {
    getItem: (k: string) => map.get(k) ?? null,
    setItem: (k: string, v: string) => void map.set(k, v),
    removeItem: (k: string) => void map.delete(k),
  } as unknown as Storage;
}

describe("first week structure", () => {
  it("seven scenes, three forks each, fourteen points on the table", () => {
    expect(FIRST_WEEK_SCENES).toHaveLength(7);
    for (const scene of FIRST_WEEK_SCENES) {
      expect(scene.choices).toHaveLength(3);
      expect(MAX_FIRST_WEEK_SCORE).toBe(14);
    }
    expect(firstWeekPoints("interview", "evidence")).toBe(2);
    expect(firstWeekPoints("interview", "wing")).toBe(1);
    expect(firstWeekPoints("interview", "off")).toBe(0);
    expect(firstWeekPoints("upload", "all")).toBe(2);
    expect(firstWeekPoints("upload", "recent")).toBe(1);
    expect(firstWeekPoints("upload", "polish")).toBe(0);
    expect(firstWeekPoints("gap", "keep")).toBe(0);
    expect(firstWeekPoints("letter", "own")).toBe(2);
    expect(firstWeekPoints("bogus", "bogus")).toBe(0);
  });

  it("is unanswered until every scene is played", () => {
    expect(firstWeekAnswered({ choices: {}, sentence: "" })).toBe(false);
    const full = Object.fromEntries(FIRST_WEEK_SCENES.map((s) => [s.id, s.choices[0].id]));
    expect(firstWeekAnswered({ choices: full, sentence: "" })).toBe(true);
  });

  it("totals only the choices it knows, and bands the week honestly", () => {
    expect(firstWeekTotal({ choices: { upload: "all", jd: "asis", interview: "evidence" }, sentence: "" })).toBe(6);
    const all2 = Object.fromEntries(FIRST_WEEK_SCENES.map((s) => [s.id, "all"]));
    // "all" is only a valid id for the upload scene — foreign entries score 0.
    expect(firstWeekTotal({ choices: all2, sentence: "" })).toBe(2);
    expect(firstWeekVerdict(12)).toBe("architect");
    expect(firstWeekVerdict(9)).toBe("architect");
    expect(firstWeekVerdict(8)).toBe("steady");
    expect(firstWeekVerdict(5)).toBe("steady");
    expect(firstWeekVerdict(4)).toBe("reluctant");
    expect(firstWeekVerdict(0)).toBe("reluctant");
  });
});

describe("first week storage round trip", () => {
  it("saves, survives, and clears", () => {
    const storage = memoryStorage();
    saveFirstWeek({ choices: { upload: "all" }, sentence: "I write it tonight." }, storage);
    expect(loadFirstWeek(storage).choices.upload).toBe("all");
    expect(loadFirstWeek(storage).sentence).toBe("I write it tonight.");
    clearFirstWeek(storage);
    expect(loadFirstWeek(storage).choices).toEqual({});
  });

  it("refuses a blob that is not JSON", () => {
    const storage = memoryStorage();
    storage.setItem("careeros.firstweek.v1", "nope {");
    expect(loadFirstWeek(storage)).toEqual({ choices: {}, sentence: "" });
  });

  it("drops keys and values it cannot recognize", () => {
    const storage = memoryStorage();
    storage.setItem(
      "careeros.firstweek.v1",
      JSON.stringify({
        choices: { upload: "all", gap: "fedor", bogus: "all" },
        sentence: 42,
      })
    );
    const loaded = loadFirstWeek(storage);
    expect(loaded.choices).toEqual({ upload: "all" });
    expect(loaded.sentence).toBe("");
  });
});
