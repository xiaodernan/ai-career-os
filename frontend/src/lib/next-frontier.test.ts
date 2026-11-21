import { describe, expect, it } from "vitest";

import { nextFrontier } from "./next-frontier";

/**
 * 369: the one direction the world points, and why that one.
 *
 * The rules are ordered by what costs the reader most to leave undone, not by what is
 * easiest to measure: a rehearsal left half-finished outranks a resume to polish, because
 * a door that closes while you are not looking is not the same as one that stays open. The
 * order is the whole claim, so it is what these tests pin.
 *
 * Silence is a real answer, not a bug: a reader with nothing waiting must not be handed an
 * errand they do not have, and a rule that cannot see its input stays silent.
 */

describe("nextFrontier", () => {
  it("names the open rehearsal first — it is the one thing a search regrets", () => {
    const frontier = nextFrontier({
      openRehearsals: 2,
      repliesToSend: 3,
      applicationsAwaitingReader: 4,
    });
    expect(frontier?.id).toBe("finish-rehearsal");
    expect(frontier?.href).toBe("/interviews");
    expect(frontier?.vars.count).toBe(2);
  });

  it("puts an unanswered letter above an application waiting on the reader", () => {
    // A reply window closes; a board row does not.
    const frontier = nextFrontier({ repliesToSend: 1, applicationsAwaitingReader: 9 });
    expect(frontier?.id).toBe("answer-reply");
    expect(frontier?.href).toBe("/replies");
  });

  it("falls to the board when only applications are waiting", () => {
    const frontier = nextFrontier({ applicationsAwaitingReader: 3 });
    expect(frontier?.id).toBe("move-application");
    expect(frontier?.href).toBe("/applications");
  });

  it("keeps reading ahead through the whole order", () => {
    expect(nextFrontier({ unreadMatches: 5 })?.id).toBe("read-matches");
    expect(nextFrontier({ unreadNotes: 2 })?.id).toBe("read-notes");
  });

  it("stays silent when nothing is waiting — an honest empty, not an invented errand", () => {
    expect(nextFrontier({})).toBeNull();
    expect(
      nextFrontier({
        openRehearsals: 0,
        repliesToSend: 0,
        applicationsAwaitingReader: 0,
        unreadMatches: 0,
        unreadNotes: 0,
      })
    ).toBeNull();
  });

  it("treats a non-number or a negative count as nothing measured", () => {
    // A payload that half-loaded must not read as a direction.
    const bad = nextFrontier({
      openRehearsals: undefined,
      repliesToSend: Number.NaN,
      applicationsAwaitingReader: -3,
    } as Parameters<typeof nextFrontier>[0]);
    expect(bad).toBeNull();
  });

  it("answers the same direction for the same ledger, every time", () => {
    // Pure by construction: a card that changes its mind on reload is a card nobody trusts.
    const input = { openRehearsals: 1 };
    expect(nextFrontier(input)).toEqual(nextFrontier(input));
  });
});
