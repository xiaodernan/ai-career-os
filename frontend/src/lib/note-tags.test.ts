import { describe, expect, it } from "vitest";

import { MAX_TAGS, formatTags, noteHref, parseTags, tagIsInert, tagRow } from "./note-tags";

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

describe("noteHref", () => {
  it("opens the kind the draft minted, not the tag all four kinds share", () => {
    expect(noteHref(["interview", "study"])).toBe("/knowledge?ntag=study");
    expect(noteHref(["interview", "answer"])).toBe("/knowledge?ntag=answer");
    expect(noteHref(["interview", "gap"])).toBe("/knowledge?ntag=gap");
    expect(noteHref(["interview", "prepare"])).toBe("/knowledge?ntag=prepare");
  });

  it("opens the whole list when there is no narrower tag to open", () => {
    expect(noteHref(["interview"])).toBe("/knowledge");
    expect(noteHref([])).toBe("/knowledge");
    expect(noteHref(undefined)).toBe("/knowledge");
    expect(noteHref(null)).toBe("/knowledge");
  });

  it("carries a tag the reader typed through the URL intact", () => {
    expect(noteHref(["interview", "system design"])).toBe("/knowledge?ntag=system%20design");
    expect(noteHref(["interview", "a&b"])).toBe("/knowledge?ntag=a%26b");
  });
});

describe("tagRow", () => {
  it("puts the five product tags first, in their own order", () => {
    expect(tagRow([])).toEqual(["interview", "study", "answer", "gap", "prepare"]);
    expect(
      tagRow([
        { tag: "study", count: 9 },
        { tag: "interview", count: 12 },
      ])
    ).toEqual(["interview", "study", "answer", "gap", "prepare"]);
  });

  it("follows them with the labels the reader typed, most-used first", () => {
    expect(
      tagRow([
        { tag: "interview", count: 12 },
        { tag: "system design", count: 4 },
        { tag: "redis", count: 2 },
        { tag: "gap", count: 1 },
      ])
    ).toEqual(["interview", "study", "answer", "gap", "prepare", "system design", "redis"]);
  });

  it("caps the reader's own labels so the row stays a filter", () => {
    const mine = Array.from({ length: 20 }, (_, i) => ({ tag: `tag-${i}`, count: 20 - i }));
    expect(tagRow(mine)).toHaveLength(12);
    expect(tagRow(mine).slice(5)).toEqual(mine.slice(0, 7).map((each) => each.tag));
    expect(tagRow(mine, 0)).toHaveLength(5);
  });
});

describe("tagIsInert", () => {
  it("is inert exactly when nothing carries it", () => {
    expect(tagIsInert(0, "study", "")).toBe(true);
    expect(tagIsInert(3, "study", "")).toBe(false);
  });

  it("stays live while it is the filter in use, even at zero", () => {
    expect(tagIsInert(0, "study", "study")).toBe(false);
    expect(tagIsInert(0, "gap", "study")).toBe(true);
  });

  it("does not call a tag empty before the counts have arrived", () => {
    // An unanswered counts read is not a zero: a row that disabled every label while
    // the query was in flight would flash every tag inert on first paint.
    expect(tagIsInert(undefined, "study", "")).toBe(false);
  });
});
