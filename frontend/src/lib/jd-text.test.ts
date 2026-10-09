import { describe, expect, it } from "vitest";

import { JD_TEXT_MIN_CHARS, jdTextIssue } from "./jd-text";

const posting = (characters: number) => "x".repeat(characters);

describe("jdTextIssue", () => {
  it("names the declared floor in the sentence it returns", () => {
    expect(jdTextIssue(posting(JD_TEXT_MIN_CHARS - 1))).toBe(
      `Paste at least ${JD_TEXT_MIN_CHARS} characters of the posting`,
    );
  });

  it("stays silent at the floor and above it", () => {
    for (const length of [JD_TEXT_MIN_CHARS, JD_TEXT_MIN_CHARS + 1, JD_TEXT_MIN_CHARS * 10]) {
      expect(jdTextIssue(posting(length))).toBeUndefined();
    }
  });

  it("judges the trimmed length, so padding cannot clear the floor", () => {
    expect(jdTextIssue(`${"  ".repeat(JD_TEXT_MIN_CHARS)}${posting(JD_TEXT_MIN_CHARS - 1)}\n`)).toBeDefined();
    expect(jdTextIssue("")).toBeDefined();
  });
});
