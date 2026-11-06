import { describe, expect, it } from "vitest";

import { mapNoteTagCounts } from "@/lib/hooks/resources";

describe("mapNoteTagCounts", () => {
  it("reads the envelope the backend actually sends", () => {
    // EnvelopeAdvice wraps a bare List<NoteTagCount> in {data: [...]}; the tag row
    // has no other way to learn which labels exist before a click.
    expect(
      mapNoteTagCounts({
        data: [
          { tag: "interview", count: 5 },
          { tag: "study", count: 2 },
        ],
      })
    ).toEqual([
      { tag: "interview", count: 5 },
      { tag: "study", count: 2 },
    ]);
  });

  it("keeps a zero count rather than dropping the label", () => {
    // A tag the reader has used up must still be a tag; "0" is the answer the row
    // prints so a click that cannot land anywhere is visibly inert.
    expect(mapNoteTagCounts({ data: [{ tag: "gap", count: 0 }] })).toEqual([
      { tag: "gap", count: 0 },
    ]);
  });

  it("accepts a payload that is already the list, and the snake-case count", () => {
    expect(mapNoteTagCounts([{ tag: " answer ", total: 3 }])).toEqual([
      { tag: "answer", count: 3 },
    ]);
  });

  it("drops rows that name no tag and rows whose count is not a number", () => {
    expect(mapNoteTagCounts({ data: [{ count: 4 }, { tag: "", count: 1 }, { tag: "x", count: "many" }] }))
      .toEqual([]);
  });

  it("answers an empty list for an empty or unexpected payload", () => {
    expect(mapNoteTagCounts({ data: [] })).toEqual([]);
    expect(mapNoteTagCounts(undefined)).toEqual([]);
    expect(mapNoteTagCounts({})).toEqual([]);
  });
});
