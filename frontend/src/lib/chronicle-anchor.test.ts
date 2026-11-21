import { describe, expect, it } from "vitest";

import { chapterAnchor, regionOf } from "./chronicle-anchor";
import type { TimelineEntry } from "@/lib/api/types";

/**
 * 370: which places a chronicle chapter is about.
 *
 * The story and the world are two readings of one ledger, and nothing connected them:
 * a chapter named what happened and never said where. The join is the engine's own
 * anchor, matched three ways because the engine writes it as whatever it had -- an
 * event's refId, a number the payload spelled, or a date. Where the anchor names
 * nothing the ledger carries the answer is empty, never a guessed region.
 */

const EVENTS: TimelineEntry[] = [
  { at: "2026-09-01T09:00:00Z", kind: "application", title: "Backend · Acme", refId: "app-1", summary: "" },
  { at: "2026-09-02T09:00:00Z", kind: "interview", title: "Rehearsal 1", refId: "iv-1", summary: "" },
  { at: "2026-09-03T09:00:00Z", kind: "note", title: "B-tree gap", refId: "note-1", summary: "" },
  { at: "2026-09-04T09:00:00Z", kind: "match", title: "Match · Beta", refId: "match-1", summary: "" },
];

describe("chapterAnchor", () => {
  it("joins a chapter to the region its anchor names", () => {
    const out = chapterAnchor({ key: "c1", title: "t", prose: "p", anchor: "iv-1" }, EVENTS);
    expect(out.regions).toEqual(["interview"]);
    expect(out.events.map((e) => e.refId)).toEqual(["iv-1"]);
    expect(out.unmatched).toBe(false);
  });

  it("reads an anchor that is a number the payload spelled", () => {
    const out = chapterAnchor({ key: "c1", title: "t", prose: "p", anchor: "1" }, EVENTS);
    expect(out.regions).toEqual(["application", "interview", "match", "note"]);
    expect(out.events).toHaveLength(4);
  });

  it("reads an anchor that is a date the chapter cited", () => {
    const out = chapterAnchor({ key: "c1", title: "t", prose: "p", anchor: "2026-09-03" }, EVENTS);
    expect(out.regions).toEqual(["note"]);
  });

  it("answers empty when the anchor names nothing the ledger carries", () => {
    // An honest gap, never a guessed region: a chapter the join cannot place is a
    // chapter that says nothing about where, rather than one that invents a place.
    const out = chapterAnchor({ key: "c1", title: "t", prose: "p", anchor: "no-such-row" }, EVENTS);
    expect(out.regions).toEqual([]);
    expect(out.unmatched).toBe(true);
  });

  it("treats a chapter with no anchor at all as unmatched", () => {
    expect(chapterAnchor({ key: "c1", title: "t", prose: "p" }, EVENTS).unmatched).toBe(true);
    expect(chapterAnchor(null, EVENTS).unmatched).toBe(true);
  });

  it("names several regions when one anchor covers several kinds", () => {
    const both: TimelineEntry[] = [
      ...EVENTS,
      { at: "2026-09-05T09:00:00Z", kind: "contact", title: "A recruiter", refId: "c-1", summary: "" },
    ];
    const out = chapterAnchor({ key: "c1", title: "t", prose: "p", anchor: "1" }, both);
    expect(out.regions).toEqual(["application", "interview", "match", "contact", "note"]);
  });
});

describe("regionOf", () => {
  it("keeps the atlas's own vocabulary and buckets the rest as unknown", () => {
    expect(regionOf("application")).toBe("application");
    expect(regionOf("a-kind-nobody-drew")).toBe("unknown");
  });
});
