import { describe, expect, it } from "vitest";

import { analyzeAnswers, unitsOf } from "@/lib/answer-echo";

/**
 * Epic 385 — the echo is arithmetic, so every expectation here is a count that can
 * be checked by hand. What matters is that the same answer always produces the same
 * numbers in both languages, and that a session with no answers produces nothing.
 */
describe("analyzeAnswers", () => {
  it("says nothing about a session that has not answered anything", () => {
    const echo = analyzeAnswers(["", "   "]);
    expect(echo.answers).toBe(0);
    expect(echo.ownership).toBeNull();
    expect(echo.nudges).toEqual([]);
  });

  it("counts a word in English and a character in Chinese with one unit", () => {
    expect(unitsOf("I led a team of 3 engineers.")).toBe(7);
    expect(unitsOf("我带了 3 个人的团队。")).toBe(9);
    const echo = analyzeAnswers(["I led a team of 3 engineers.", "我带了 3 个人的团队。"]);
    expect(echo.answers).toBe(2);
    expect(echo.units).toBe(16);
    expect(echo.avgUnits).toBe(8);
    expect(echo.numbers).toBe(2);
  });

  it("counts sentence size from real sentence ends in both scripts", () => {
    const echo = analyzeAnswers(["I shipped it. Then I watched the logs! Did it hold?", "先上线。然后盯日志。最后看曲线。"]);
    expect(echo.sentences).toBe(6);
    expect(echo.avgSentence).toBe(4);
  });

  it("finds fillers in both languages and ranks the loudest first", () => {
    const english = analyzeAnswers(["Um, um, you know, I basically led it."]);
    expect(english.fillers.map((f) => f.term)).toEqual(["um", "basically", "you know"]);

    const mixed = analyzeAnswers([
      "Um, um, you know, I basically led it.",
      "嗯，那个，就是说，我做了。",
    ]);
    expect(mixed.fillers[0]).toEqual({ term: "um", count: 2 });
    // Four at most reach the shelf, the loudest first.
    expect(mixed.fillers.length).toBe(4);
    expect(mixed.fillerTotal).toBe(7);
  });

  it("separates hedges from fillers and counts them without merging", () => {
    const echo = analyzeAnswers(["I think it maybe worked, perhaps.", "可能吧，大概是。"]);
    expect(echo.hedges).toBe(5);
    expect(echo.fillerTotal).toBe(0);
  });

  it("weighs the singular voice against the plural, never double-counting 我们", () => {
    const english = analyzeAnswers(["I led my team; we shipped it."]);
    expect(english.singular).toBe(2);
    expect(english.plural).toBe(1);
    expect(english.ownership).toBeCloseTo(2 / 3);

    const chinese = analyzeAnswers(["我们做了这个项目，我负责后端。"]);
    expect(chinese.singular).toBe(1);
    expect(chinese.plural).toBe(1);
    expect(chinese.ownership).toBeCloseTo(0.5);
  });

  it("nudges on short answers and on a voice that never reaches for a number", () => {
    const short = analyzeAnswers(["I led it."]);
    expect(short.nudges.map((n) => n.key)).toContain("interviews.detail.echoNudgeShort");
    // One answer is not a pattern: "no numbers yet" waits for the second answer.
    expect(short.nudges.map((n) => n.key)).not.toContain("interviews.detail.echoNudgeNoNumbers");

    const pair = analyzeAnswers(["I led the migration end to end and it held.", "I wrote the runbook nobody read."]);
    expect(pair.nudges.map((n) => n.key)).toContain("interviews.detail.echoNudgeNoNumbers");
  });

  it("names the plural voice when the team speaks more than the reader", () => {
    const echo = analyzeAnswers(["We shipped it. We shipped it. We shipped it."]);
    expect(echo.nudges.map((n) => n.key)).toContain("interviews.detail.echoNudgeWe");
    expect(echo.nudges.map((n) => n.key)).toContain("interviews.detail.echoNudgeShort");
  });

  it("keeps at most four nudges and lets the longest answer be information, not a warning", () => {
    const long = Array.from({ length: 230 }, () => "word").join(" ");
    const echo = analyzeAnswers([long, "um um"]);
    expect(echo.nudges.length).toBe(4);
    const longNudge = echo.nudges.find((n) => n.key === "interviews.detail.echoNudgeLong");
    expect(longNudge).toEqual({ key: "interviews.detail.echoNudgeLong", vars: { longest: 230 }, watch: false });
    expect(echo.nudges.map((n) => n.key)).toContain("interviews.detail.echoNudgeRambling");
  });

  it("points every nudge at an i18n key rather than a sentence", () => {
    const echo = analyzeAnswers(["Um, I led it."]);
    for (const nudge of echo.nudges) expect(nudge.key).toMatch(/^interviews\.detail\.echoNudge/);
  });
});
