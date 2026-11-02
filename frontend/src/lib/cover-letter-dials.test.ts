import { describe, expect, it } from "vitest";

import {
  COVER_LETTER_LENGTHS,
  COVER_LETTER_TONES,
  UNSET_DIAL,
  dialOptions,
  dialsOf,
  dialsToWire,
  dialSeed,
  letterRewriteHref,
} from "./cover-letter-dials";
import { translations } from "./i18n/translations";

describe("UNSET_DIAL", () => {
  it("is a value Radix accepts, so the 'Not set' option can exist at all", () => {
    expect(UNSET_DIAL).not.toBe("");
  });
});

describe("dialsOf", () => {
  it("keeps the dials the letter was kept with", () => {
    expect(dialsOf({ tone: "warm", length: "short" })).toEqual({ tone: "warm", length: "short" });
  });
  it("reads a dial nobody set as the explicit unset, not as a missing field", () => {
    expect(dialsOf({ tone: null, length: null })).toEqual({ tone: UNSET_DIAL, length: UNSET_DIAL });
    expect(dialsOf({})).toEqual({ tone: UNSET_DIAL, length: UNSET_DIAL });
  });
});

describe("dialsToWire", () => {
  it("sends the unset back as the empty string the route reads as 'clear it'", () => {
    expect(dialsToWire({ tone: UNSET_DIAL, length: UNSET_DIAL })).toEqual({ tone: "", length: "" });
  });
  it("passes a chosen value through untouched", () => {
    expect(dialsToWire({ tone: "confident", length: "detailed" })).toEqual({
      tone: "confident",
      length: "detailed",
    });
  });
});

describe("dialOptions", () => {
  it("adds a stored value the catalogue does not know, rather than hiding it", () => {
    const options = dialOptions(COVER_LETTER_TONES, "warm");

    expect(options[0]).toEqual({ value: "warm", labelKey: "" });
    expect(options).toHaveLength(COVER_LETTER_TONES.length + 1);
  });
  it("leaves a known value and the explicit unset against the plain catalogue", () => {
    expect(dialOptions(COVER_LETTER_LENGTHS, "detailed")).toBe(COVER_LETTER_LENGTHS);
    expect(dialOptions(COVER_LETTER_LENGTHS, UNSET_DIAL)).toBe(COVER_LETTER_LENGTHS);
  });
});

describe("the dial catalogue", () => {
  it("names every option in both languages", () => {
    const keys = [...COVER_LETTER_TONES, ...COVER_LETTER_LENGTHS].map((option) => option.labelKey);
    for (const key of keys) {
      expect(Object.keys(translations.en.coverLetter)).toContain(key.split(".")[1]);
      expect(Object.keys(translations.zh.coverLetter)).toContain(key.split(".")[1]);
    }
  });
});

describe("letterRewriteHref", () => {
  it("carries the catalogue dials and the anchor the drafting card owns", () => {
    expect(letterRewriteHref("job-1", { tone: "formal", length: "short" })).toBe(
      "/jobs/job-1?tone=formal&length=short#cover-letter"
    );
  });

  it("leaves out a dial the catalogue does not know rather than preselecting nothing", () => {
    expect(letterRewriteHref("job-1", { tone: "warm", length: "short" })).toBe(
      "/jobs/job-1?length=short#cover-letter"
    );
  });

  it("still lands on the drafting card when no dial was set", () => {
    expect(letterRewriteHref("job-1", { tone: null, length: null })).toBe(
      "/jobs/job-1#cover-letter"
    );
  });
});

describe("dialSeed", () => {
  it("adopts the dials the address carries", () => {
    expect(dialSeed("?tone=formal&length=short", { tone: "balanced", length: "standard" })).toEqual({
      tone: "formal",
      length: "short",
    });
  });

  it("keeps the defaults for anything a hand-edited address carries", () => {
    const fallback = { tone: "balanced", length: "standard" };
    expect(dialSeed("?tone=shouty&length=epic", fallback)).toEqual(fallback);
    expect(dialSeed("", fallback)).toEqual(fallback);
  });
});