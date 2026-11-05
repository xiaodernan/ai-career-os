import { describe, expect, it } from "vitest";

import { MAX_TAGS, formatTags, parseTags } from "./note-tags";

describe("parseTags", () => {
  it("splits on commas in either language and trims what is left", () => {
    expect(parseTags(" interview , study，gap ")).toEqual(["interview", "study", "gap"]);
    expect(parseTags("a\nb")).toEqual(["a", "b"]);
  });

  it("folds case and drops duplicates so one tag is one chip", () => {
    expect(parseTags("Interview, interview, INTERVIEW")).toEqual(["interview"]);
  });

  it("keeps tags short and few: eight labels of at most 32 characters", () => {
    const many = Array.from({ length: 12 }, (_, i) => `tag-${i}`).join(",");
    expect(parseTags(many)).toHaveLength(MAX_TAGS);
    expect(parseTags("x".repeat(50))).toEqual(["x".repeat(32)]);
  });

  it("answers an empty list for an empty input", () => {
    expect(parseTags("")).toEqual([]);
    expect(parseTags("   ,  ")).toEqual([]);
    expect(parseTags(undefined)).toEqual([]);
  });
});

describe("formatTags", () => {
  it("writes a note's tags back into the one input", () => {
    expect(formatTags(["interview", "gap"])).toBe("interview, gap");
    expect(formatTags([])).toBe("");
    expect(formatTags(undefined)).toBe("");
  });
});
