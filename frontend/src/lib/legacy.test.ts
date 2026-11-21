import { describe, expect, it } from "vitest";

import { legacyOf } from "./legacy";

/**
 * 371: what one search leaves behind for the next one.
 *
 * Three rules, each naming the facts that fired it and silent when its input is
 * absent. The claims pinned here are the order of the lesson (what the ledger can
 * actually prove) and the silence (a thin ledger gets no lesson rather than a
 * platitude).
 */

describe("legacyOf", () => {
  it("names the material a next search starts from, in a fixed order", () => {
    const out = legacyOf({
      rehearsals: 4,
      reportsWritten: 2,
      letters: 3,
      notesKept: 6,
      offers: 1,
    });
    expect(out.reuse.map((row) => row.id)).toEqual(["reports", "letters", "notes", "offers"]);
    expect(out.reuse[0].count).toBe(2);
    expect(out.reuse[0].href).toBe("/interviews");
  });

  it("keeps only the material that exists", () => {
    const out = legacyOf({ reportsWritten: 1 });
    expect(out.reuse.map((row) => row.id)).toEqual(["reports"]);
  });

  it("names the stage that cost the most, ties broken by id", () => {
    const out = legacyOf({ stages: { applied: 12, interview: 5, screening: 5 } });
    expect(out.costliestStage).toEqual({ id: "applied", count: 12 });
    const tie = legacyOf({ stages: { screening: 5, interview: 5 } });
    expect(tie.costliestStage).toEqual({ id: "interview", count: 5 });
  });

  it("answers no stage when the board is empty", () => {
    expect(legacyOf({}).costliestStage).toBeNull();
    expect(legacyOf({ stages: { applied: 0 } }).costliestStage).toBeNull();
  });

  it("teaches finishing when rehearsals outran the reports they produced", () => {
    // The ledger can prove this one: five rehearsals, one report.
    const out = legacyOf({ rehearsals: 5, reportsWritten: 1 });
    expect(out.lesson?.titleKey).toBe("legacy.lessonUnfinishedTitle");
  });

  it("teaches reading back when notes were kept and never used", () => {
    const out = legacyOf({ notesKept: 6, rehearsals: 2, reportsWritten: 2 });
    expect(out.lesson?.titleKey).toBe("legacy.lessonUnusedTitle");
  });

  it("teaches reuse when the letters did the work", () => {
    const out = legacyOf({ letters: 4 });
    expect(out.lesson?.titleKey).toBe("legacy.lessonReusedTitle");
  });

  it("gives a thin ledger no lesson at all, rather than a platitude", () => {
    expect(legacyOf({}).lesson).toBeNull();
    expect(legacyOf({ rehearsals: 1, reportsWritten: 1 }).lesson).toBeNull();
  });

  it("treats a non-number as nothing measured", () => {
    const out = legacyOf({
      rehearsals: undefined,
      reportsWritten: Number.NaN,
      letters: -2,
      notesKept: 0,
      offers: 0,
    } as Parameters<typeof legacyOf>[0]);
    expect(out.reuse).toEqual([]);
    expect(out.lesson).toBeNull();
  });
});
