/**
 * 370: which places a chronicle chapter is about.
 *
 * The chronicle (Epic 354) is the story; the atlas (Epic 357) is the world. They are
 * two readings of the same ledger and nothing connected them: a chapter named what
 * happened and never said where, so a reader who believed the chapter had no way to
 * go and stand in the room it described.
 *
 * The engine anchors every chapter to a milestone or event number it was written
 * from. That anchor is the join: this module finds the timeline events a chapter's
 * anchor names, and the regions those events live in. Where the anchor names nothing
 * the ledger carries, the answer is empty -- an honest gap, never a guessed region.
 *
 * Pure and total: no event, no chapter, no anchor is an error. The same inputs always
 * answer the same regions, so the card can render without a browser.
 */

import type { TimelineEntry } from "@/lib/api/types";
import type { ChronicleChapter } from "@/lib/api/types";

export interface ChapterAnchor {
  /** The regions the chapter is about, in the atlas's own order. */
  regions: string[];
  /** The events the anchor named, so a caller can count or link them. */
  events: TimelineEntry[];
  /** True when the chapter's anchor named nothing this ledger carries. */
  unmatched: boolean;
}

const REGION_ORDER = [
  "application",
  "interview",
  "match",
  "contact",
  "resume_version",
  "note",
  "unknown",
] as const;

/** The kinds the atlas draws, in its own order, for a region name that is not one. */
export function regionOf(kind: string): string {
  return (REGION_ORDER as readonly string[]).includes(kind) ? kind : "unknown";
}

/**
 * The regions one chapter is about.
 *
 * The anchor is matched three ways, because the engine writes it as whatever it had:
 * an event's own refId, a milestone key, or a bare number the payload spelled. Each
 * is tried in that order and the first that names a real event wins, so a chapter
 * anchored to a refId is never misread as a number.
 */
export function chapterAnchor(
  chapter: ChronicleChapter | null | undefined,
  events: readonly TimelineEntry[],
): ChapterAnchor {
  const anchor = (chapter?.anchor ?? "").trim();
  if (!anchor) return { regions: [], events: [], unmatched: true };

  const byRefId = events.filter((event) => event.refId === anchor);
  if (byRefId.length > 0) return finish(byRefId);

  // A milestone key or counter name: the ledger does not carry one as a refId, but a
  // chapter anchored to a number may still name an event whose refId ends in it.
  const bySuffix = events.filter(
    (event) => event.refId.length > 0 && event.refId.endsWith(anchor),
  );
  if (bySuffix.length > 0) return finish(bySuffix);

  // A date the payload spelled: the chapter cites the day it happened.
  const byDate = events.filter((event) => event.at.startsWith(anchor));
  if (byDate.length > 0) return finish(byDate);

  return { regions: [], events: [], unmatched: true };
}

function finish(matched: readonly TimelineEntry[]): ChapterAnchor {
  const kinds = new Set(matched.map((event) => regionOf(event.kind)));
  const regions = REGION_ORDER.filter((kind) => kinds.has(kind));
  return { regions: [...regions], events: [...matched], unmatched: false };
}
