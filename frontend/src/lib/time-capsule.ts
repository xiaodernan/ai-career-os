/**
 * The sealed letter (Epic 384).
 *
 * A reader can write to their future self and set a date on which the letter
 * opens. There is no new table and no new endpoint: a capsule is an ordinary
 * `user_note` carrying the `capsule` tag plus one dated tag. That keeps the
 * letter inside the data export the reader already owns, and it means the only
 * thing the product has to get right is the arithmetic of the seal.
 *
 * Sealing is a UI contract, not encryption: the note's body is still in the
 * reader's own database, exactly like every other note. The card does not render
 * a sealed body, which is the promise a personal ritual needs. Anyone who wants
 * to read their own note early can open the notes page; nothing is hidden from
 * its owner, only from the passing glance.
 */

import type { KnowledgeNote } from "@/lib/api/types";

export const CAPSULE_TAG = "capsule";
const DATE_PREFIX = "capsule-";

/** `YYYY-MM-DD` in the reader's own clock, never UTC-shifted. */
export function localDateKey(date: Date = new Date()): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function validDateKey(value: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const parsed = new Date(`${value}T00:00:00`);
  return Number.isFinite(parsed.getTime()) && localDateKey(parsed) === value;
}

/** A local date `days` from `from`, used to pre-fill the seal's date input. */
export function addDays(days: number, from: Date = new Date()): string {
  const next = new Date(from);
  next.setDate(next.getDate() + days);
  return localDateKey(next);
}

/** The date a capsule opens, or null if this note is not a capsule. */
export function capsuleDate(note: Pick<KnowledgeNote, "tags">): string | null {
  for (const tag of note.tags ?? []) {
    if (!tag.startsWith(DATE_PREFIX)) continue;
    const value = tag.slice(DATE_PREFIX.length);
    if (validDateKey(value)) return value;
  }
  return null;
}

/** A capsule is sealed while its date is in the future. */
export function isSealed(revealDate: string, today: string = localDateKey()): boolean {
  return revealDate > today;
}

/** Whole days until the seal opens; 0 on the opening day and for open letters. */
export function daysUntil(revealDate: string, today: string = localDateKey()): number {
  const target = new Date(`${revealDate}T00:00:00`).getTime();
  const now = new Date(`${today}T00:00:00`).getTime();
  if (!Number.isFinite(target) || !Number.isFinite(now)) return 0;
  return Math.max(0, Math.round((target - now) / 86_400_000));
}

/** The tags a new capsule is stored with; the date tag is what opens it. */
export function buildCapsuleTags(revealDate: string): string[] {
  return [CAPSULE_TAG, `${DATE_PREFIX}${revealDate}`];
}

export interface Capsule {
  note: KnowledgeNote;
  revealDate: string;
  sealed: boolean;
  days: number;
}

/**
 * Sealed letters first, soonest-opening at the top; open letters newest first.
 * A note carrying the tag but no readable date is not a capsule and is dropped
 * rather than guessed at.
 */
export function readCapsules(
  notes: KnowledgeNote[] | undefined,
  today: string = localDateKey(),
): Capsule[] {
  const capsules: Capsule[] = [];
  for (const note of notes ?? []) {
    const revealDate = capsuleDate(note);
    if (!revealDate) continue;
    capsules.push({
      note,
      revealDate,
      sealed: isSealed(revealDate, today),
      days: daysUntil(revealDate, today),
    });
  }
  return capsules.sort((a, b) => {
    if (a.sealed !== b.sealed) return a.sealed ? -1 : 1;
    return a.sealed ? a.revealDate.localeCompare(b.revealDate) : b.revealDate.localeCompare(a.revealDate);
  });
}
