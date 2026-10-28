import { describe, expect, it } from "vitest";

import { JD_TEXT_MIN_CHARS, jdTextIssue } from "./jd-text";
import { fill, lookup } from "./i18n/locale-context";
import { translations } from "./i18n/translations";

const posting = (characters: number) => "x".repeat(characters);

const en = (key: string, vars?: Record<string, string | number>) => {
  const value = lookup(translations.en, key);
  if (value === undefined) throw new Error(`the English table has no ${key}`);
  return fill(value, vars);
};

describe("jdTextIssue", () => {
  it("names the declared floor in the issue it answers", () => {
    expect(jdTextIssue(posting(JD_TEXT_MIN_CHARS - 1))).toEqual({
      key: "jd.pasteAtLeast",
      params: { min: JD_TEXT_MIN_CHARS },
    });
  });

  it("has a sentence in both languages, with the floor filled in", () => {
    const issue = jdTextIssue("");
    expect(issue).toBeDefined();
    if (issue === undefined) return;
    expect(en(issue.key, issue.params)).toBe(
      `Paste at least ${JD_TEXT_MIN_CHARS} characters of the posting`,
    );
    expect(lookup(translations.zh, issue.key)).toBeTypeOf("string");
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
