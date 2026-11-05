import { describe, expect, it } from "vitest";

import { cardPractice, previousRehearsal } from "./interview-practice";

/**
 * 59.1: the practice line is a fold over the card's rehearsals.
 *
 * The three things it can get wrong are all about not inventing data: a free
 * rehearsal has no line, an ungraded history has no best, and a session the
 * page did not reach is still placed rather than dropped.
 */
const rows = [
  { id: "s3", overall: 71, startedAt: "2026-11-03T10:00:00Z" },
  { id: "s1", overall: 58, startedAt: "2026-11-01T10:00:00Z" },
  { id: "s2", overall: undefined, startedAt: "2026-11-02T10:00:00Z" },
];

describe("cardPractice", () => {
  it("places the session in the card's history, oldest first", () => {
    // The list arrives newest first; the position is the reader's word, so it
    // has to count from the beginning of the practice, not the top of the page.
    expect(cardPractice(rows, "s3")).toEqual({ position: 3, count: 3, best: 71 });
    expect(cardPractice(rows, "s1")).toEqual({ position: 1, count: 3, best: 71 });
  });

  it("reports the best graded score and ignores an ungraded sitting", () => {
    expect(cardPractice(rows, "s2")).toEqual({ position: 2, count: 3, best: 71 });
    expect(cardPractice([{ id: "a", startedAt: "2026-11-01T10:00:00Z" }], "a")).toEqual({
      position: 1,
      count: 1,
    });
  });

  it("has no line for a free rehearsal or an empty history", () => {
    expect(cardPractice(rows, null)).toBeNull();
    expect(cardPractice(rows, "someone-else")).toBeNull();
    expect(cardPractice([], "s1")).toBeNull();
  });
});

describe("previousRehearsal", () => {
  it("picks the newest finished sibling, not the one being taken", () => {
    const previous = previousRehearsal(
      [
        { id: "current", startedAt: "2026-11-05T10:00:00Z", status: "active" },
        { id: "older", startedAt: "2026-11-01T10:00:00Z", status: "completed" },
        { id: "newer", startedAt: "2026-11-03T10:00:00Z", status: "completed" },
      ],
      "current"
    );
    expect(previous?.id).toBe("newer");
  });

  it("counts only completed rehearsals: a half-finished one has no report", () => {
    const previous = previousRehearsal(
      [
        { id: "current", startedAt: "2026-11-05T10:00:00Z", status: "active" },
        { id: "abandoned", startedAt: "2026-11-04T10:00:00Z", status: "abandoned" },
        { id: "done", startedAt: "2026-11-02T10:00:00Z", status: "completed" },
      ],
      "current"
    );
    expect(previous?.id).toBe("done");
  });

  it("answers nothing for a free rehearsal or a card with no history", () => {
    expect(previousRehearsal([{ id: "a", status: "completed" }], null)).toBeNull();
    expect(previousRehearsal([{ id: "current", status: "active" }], "current")).toBeNull();
    expect(previousRehearsal([], "current")).toBeNull();
  });
});
