import { describe, expect, it } from "vitest";

import {
  addDays,
  buildCapsuleTags,
  capsuleDate,
  daysUntil,
  isSealed,
  readCapsules,
  type Capsule,
} from "./time-capsule";
import type { KnowledgeNote } from "@/lib/api/types";

const TODAY = "2026-11-22";

function note(tags: string[], content = "a letter"): KnowledgeNote {
  return { id: tags.join("-"), title: "Time capsule", content, tags };
}

describe("capsuleDate", () => {
  it("reads the dated tag and ignores every other tag", () => {
    expect(capsuleDate(note(["capsule", "capsule-2027-06-01", "study"]))).toBe("2027-06-01");
  });

  it("refuses a malformed or impossible date instead of guessing", () => {
    expect(capsuleDate(note(["capsule-2027-13-01"]))).toBeNull();
    expect(capsuleDate(note(["capsule-2027-02-30"]))).toBeNull();
    expect(capsuleDate(note(["capsule"]))).toBeNull();
    expect(capsuleDate(note([]))).toBeNull();
  });
});

describe("the seal", () => {
  it("is closed until the date, open on the day itself", () => {
    expect(isSealed("2026-11-23", TODAY)).toBe(true);
    expect(isSealed("2026-11-22", TODAY)).toBe(false);
    expect(isSealed("2026-11-21", TODAY)).toBe(false);
  });

  it("counts whole local days across a month and a year boundary", () => {
    expect(daysUntil("2026-11-22", TODAY)).toBe(0);
    expect(daysUntil("2026-11-23", TODAY)).toBe(1);
    expect(daysUntil("2026-12-01", TODAY)).toBe(9);
    expect(daysUntil("2027-01-01", TODAY)).toBe(40);
  });
});

describe("readCapsules", () => {
  it("puts sealed letters first, soonest to open, then open letters newest first", () => {
    const capsules: Capsule[] = readCapsules(
      [
        note(["capsule-2025-01-01"], "already open"),
        note(["capsule-2027-06-01"], "far"),
        note(["capsule-2026-12-01"], "soon"),
        note(["capsule"], "not a capsule"),
      ],
      TODAY,
    );
    expect(capsules.map((c) => c.revealDate)).toEqual([
      "2026-12-01",
      "2027-06-01",
      "2025-01-01",
    ]);
    expect(capsules[0].sealed).toBe(true);
    expect(capsules[2].sealed).toBe(false);
  });

  it("survives an undefined shelf", () => {
    expect(readCapsules(undefined, TODAY)).toEqual([]);
  });
});

describe("buildCapsuleTags", () => {
  it("mints the tag the list reads and the dated tag the seal reads", () => {
    expect(buildCapsuleTags("2027-06-01")).toEqual(["capsule", "capsule-2027-06-01"]);
  });
});

describe("addDays", () => {
  it("crosses a month and pre-fills a local date", () => {
    expect(addDays(90, new Date(2026, 10, 22))).toBe("2027-02-20");
    expect(addDays(1, new Date(2026, 11, 31))).toBe("2027-01-01");
  });
});
