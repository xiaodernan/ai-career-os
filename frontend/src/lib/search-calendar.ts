/**
 * Epic 386 — the month of the search. The product already writes dated rows in
 * seven places, but no screen lays them on a calendar: a reminder, a rehearsal,
 * a contact gone cold and a sealed letter are all "a day" to the reader, and the
 * reader plans in days. This module is the pure fold that puts them there.
 *
 * It is arithmetic over rows the page already holds — no endpoint, no model call.
 * A row whose date cannot be read is dropped rather than guessed, and a sealed
 * capsule contributes its opening date only, never its body.
 */

import type { Application, FollowUpItem, InterviewSession, KnowledgeNote } from "@/lib/api/types";
import { addDays, localDateKey, readCapsules } from "@/lib/time-capsule";

export type CalendarKind = "reminder" | "interview" | "followup" | "capsule";

export interface CalendarEvent {
  id: string;
  /** `YYYY-MM-DD` in the reader's own clock. */
  date: string;
  kind: CalendarKind;
  /** The row's own words (a role, a company, a name); never a sentence this module invented. */
  title: string;
  detail?: string;
  href?: string;
}

export interface MonthCell {
  date: string;
  inMonth: boolean;
}

const KIND_ORDER: CalendarKind[] = ["reminder", "followup", "interview", "capsule"];

/** A local `YYYY-MM` for a date; the calendar never shifts a row into another month by UTC. */
export function monthKeyOf(date: Date = new Date()): string {
  return localDateKey(date).slice(0, 7);
}

/** A year-month from anywhere, or null when it is not one. */
export function readMonthKey(value: string | undefined | null): string | null {
  if (!value || !/^\d{4}-\d{2}$/.test(value)) return null;
  const month = Number(value.slice(5, 7));
  return month >= 1 && month <= 12 ? value : null;
}

export function shiftMonth(key: string, delta: number): string {
  const year = Number(key.slice(0, 4));
  const month = Number(key.slice(5, 7));
  const moved = new Date(year, month - 1 + delta, 1);
  return monthKeyOf(moved);
}

/** The date key for an instant, in the reader's own clock; null when unreadable. */
export function dateKeyOf(iso: string | null | undefined): string | null {
  if (!iso) return null;
  const parsed = new Date(iso);
  if (!Number.isFinite(parsed.getTime())) return null;
  return localDateKey(parsed);
}

/**
 * Six Monday-first weeks, always 42 cells, so the grid never changes height when
 * the reader walks from a short month to a long one.
 */
export function monthCells(key: string): MonthCell[] {
  const year = Number(key.slice(0, 4));
  const month = Number(key.slice(5, 7));
  const first = new Date(year, month - 1, 1);
  const offset = (first.getDay() + 6) % 7;
  const start = new Date(year, month - 1, 1 - offset);
  return Array.from({ length: 42 }, (_, index) => {
    const day = new Date(start);
    day.setDate(start.getDate() + index);
    return { date: localDateKey(day), inMonth: day.getMonth() === month - 1 };
  });
}

/** The day a follow-up becomes due: the last touch plus the relation's cadence. */
export function followUpDue(item: FollowUpItem, today: string = localDateKey()): string | null {
  const since = item.daysSince;
  const cadence = item.cadenceDays;
  if (typeof since !== "number" || !Number.isFinite(since)) return null;
  if (typeof cadence !== "number" || !Number.isFinite(cadence) || cadence <= 0) return null;
  return addDays(Math.round(cadence - since), new Date(`${today}T00:00:00`));
}

export interface CalendarInput {
  applications?: Application[];
  interviews?: InterviewSession[];
  followUps?: FollowUpItem[];
  notes?: KnowledgeNote[];
  today?: string;
}

export function buildEvents(input: CalendarInput): CalendarEvent[] {
  const today = input.today ?? localDateKey();
  const events: CalendarEvent[] = [];

  for (const application of input.applications ?? []) {
    const date = dateKeyOf(application.reminderAt);
    if (!date) continue;
    events.push({
      id: `reminder-${application.id}`,
      date,
      kind: "reminder",
      title: application.title,
      detail: application.companyName ?? application.status,
      href: `/applications?application=${application.id}`,
    });
  }

  for (const session of input.interviews ?? []) {
    const date = dateKeyOf(session.startedAt);
    if (!date) continue;
    events.push({
      id: `interview-${session.id}`,
      date,
      kind: "interview",
      title: session.jobTitle || session.companyName || session.mode,
      detail: session.companyName ?? undefined,
      href: `/interviews/${session.id}`,
    });
  }

  for (const item of input.followUps ?? []) {
    const date = followUpDue(item, today);
    if (!date) continue;
    events.push({
      id: `followup-${item.id}`,
      date,
      kind: "followup",
      title: item.name || item.id,
      detail: item.company ?? item.relation ?? undefined,
      href: "/networking",
    });
  }

  for (const capsule of readCapsules(input.notes, today)) {
    events.push({
      id: `capsule-${capsule.note.id}`,
      date: capsule.revealDate,
      kind: "capsule",
      // A sealed letter contributes its envelope, not its prose — the note's title
      // is empty for every capsule the timeline writes, so this stays a date.
      title: capsule.note.title ?? "",
      href: "/timeline",
    });
  }

  return events.sort(
    (a, b) =>
      a.date.localeCompare(b.date) ||
      KIND_ORDER.indexOf(a.kind) - KIND_ORDER.indexOf(b.kind) ||
      a.title.localeCompare(b.title)
  );
}

/** Events grouped by day, in the same order `buildEvents` returned them. */
export function eventsByDate(events: CalendarEvent[]): Map<string, CalendarEvent[]> {
  const grouped = new Map<string, CalendarEvent[]>();
  for (const event of events) {
    const list = grouped.get(event.date);
    if (list) list.push(event);
    else grouped.set(event.date, [event]);
  }
  return grouped;
}

/** The month's own events, grouped — what the grid reads. */
export function eventsInMonth(events: CalendarEvent[], key: string): Map<string, CalendarEvent[]> {
  return eventsByDate(events.filter((event) => event.date.startsWith(`${key}-`)));
}

export function summarize(events: CalendarEvent[]): Record<CalendarKind, number> {
  const counts: Record<CalendarKind, number> = {
    reminder: 0,
    interview: 0,
    followup: 0,
    capsule: 0,
  };
  for (const event of events) counts[event.kind] += 1;
  return counts;
}

/** The first event on or after today, with the reader able to see the whole list too. */
export function nextEvent(events: CalendarEvent[], today: string = localDateKey()): CalendarEvent | null {
  return events.find((event) => event.date >= today) ?? null;
}
