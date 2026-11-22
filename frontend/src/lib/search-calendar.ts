/**
 * Epic 386 — the month of the search. The product already writes dated rows in
 * seven places, but no screen lays them on a calendar: a reminder, a rehearsal,
 * a contact gone cold and a sealed letter are all "a day" to the reader, and the
 * reader plans in days. This module is the pure fold that puts them there.
 *
 * It is arithmetic over rows the page already holds — no endpoint, no model call.
 * A row whose date cannot be read is dropped rather than guessed; a sealed
 * capsule contributes its opening date only, never its body; a decided offer is
 * no longer a question and stays off.
 */

import type { Application, FollowUpItem, InterviewSession, KnowledgeNote, OfferShelfItem } from "@/lib/api/types";
import { addDays, localDateKey, readCapsules } from "@/lib/time-capsule";

export type CalendarKind = "reminder" | "interview" | "followup" | "offer" | "capsule";

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

export type CalendarView = "month" | "week";

/** Only an exact `week` switches the grid; anything else leaves the month standing. */
export function readCalendarView(value: string | undefined | null): CalendarView {
  return value === "week" ? "week" : "month";
}

/** A real `YYYY-MM-DD` in the reader's clock, or null — 2026-02-30 is not a day. */
export function readDayKey(value: string | undefined | null): string | null {
  if (!value || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return null;
  const parsed = new Date(`${value}T00:00:00`);
  if (!Number.isFinite(parsed.getTime())) return null;
  return localDateKey(parsed) === value ? value : null;
}

/** Walk a day forward or back across months and years without a UTC shift. */
export function shiftDays(date: string, delta: number): string {
  const moved = new Date(`${date}T00:00:00`);
  moved.setDate(moved.getDate() + delta);
  return localDateKey(moved);
}

/**
 * The Monday-first week around a day — always seven cells, so the reader who
 * steps a week at a time sees the same columns Monday through Sunday.
 */
export function weekCells(date: string): MonthCell[] {
  const anchor = new Date(`${date}T00:00:00`);
  const month = anchor.getMonth();
  const offset = (anchor.getDay() + 6) % 7;
  const start = new Date(anchor);
  start.setDate(anchor.getDate() - offset);
  return Array.from({ length: 7 }, (_, index) => {
    const day = new Date(start);
    day.setDate(start.getDate() + index);
    return { date: localDateKey(day), inMonth: day.getMonth() === month };
  });
}

const KIND_ORDER: CalendarKind[] = ["reminder", "followup", "interview", "offer", "capsule"];

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
  /** The offer shelf (Epic 185): a pending deadline is a dated decision. */
  offers?: OfferShelfItem[];
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

  for (const offer of input.offers ?? []) {
    // A decided offer is no longer a question; the backend's feed filters the
    // same way, so the page and the subscription cannot disagree.
    if (offer.decision && offer.decision !== "pending") continue;
    const date = dateKeyOf(offer.deadline);
    if (!date) continue;
    events.push({
      id: `offer-${offer.id}`,
      date,
      kind: "offer",
      title: offer.label,
      href: "/offers",
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

/** The seven days around a date, grouped — the week grid reads this and never a month. */
export function eventsInWeek(events: CalendarEvent[], date: string): Map<string, CalendarEvent[]> {
  const first = weekCells(date)[0].date;
  const last = shiftDays(first, 6);
  return eventsByDate(events.filter((event) => event.date >= first && event.date <= last));
}

export interface WeekTempo {
  total: number;
  /** Days in the week that carry at least one row. */
  activeDays: number;
  /** Days in the week that carry none. */
  openDays: number;
  /** The fullest day; ties go to the earlier day in the week. */
  busiest: { date: string; count: number } | null;
}

/**
 * Epic 395 — the week's own rhythm, read off the seven cells the grid draws.
 * Pure counting: no row is added or weighted, and a tie is not broken by
 * importance, only by the order the reader already sees.
 */
export function weekTempo(
  cells: MonthCell[],
  events: Map<string, CalendarEvent[]>
): WeekTempo {
  let total = 0;
  let activeDays = 0;
  let busiest: { date: string; count: number } | null = null;
  for (const cell of cells) {
    const count = events.get(cell.date)?.length ?? 0;
    total += count;
    if (count > 0) activeDays += 1;
    if (count > 0 && (busiest === null || count > busiest.count)) {
      busiest = { date: cell.date, count };
    }
  }
  return { total, activeDays, openDays: cells.length - activeDays, busiest };
}

export function summarize(events: CalendarEvent[]): Record<CalendarKind, number> {
  const counts: Record<CalendarKind, number> = {
    reminder: 0,
    interview: 0,
    followup: 0,
    offer: 0,
    capsule: 0,
  };
  for (const event of events) counts[event.kind] += 1;
  return counts;
}

/** The first event on or after today, with the reader able to see the whole list too. */
export function nextEvent(events: CalendarEvent[], today: string = localDateKey()): CalendarEvent | null {
  return upcomingEvents(events, today, 1)[0] ?? null;
}

/**
 * Epic 405 — the three kinds that ask the reader for something. A rehearsal
 * that happened and a letter that opened are history, not debt: they stay in
 * the grid and are never late. A reminder that fired, a follow-up whose cadence
 * ran out, and an offer deadline that passed while the decision is pending are
 * questions the reader still owes an answer.
 */
export const OVERDUE_KINDS: CalendarKind[] = ["reminder", "followup", "offer"];

/** Whole days a date sits before today; 0 on or after today and when unreadable. */
export function daysPast(date: string, today: string = localDateKey()): number {
  const target = new Date(`${date}T00:00:00`).getTime();
  const now = new Date(`${today}T00:00:00`).getTime();
  if (!Number.isFinite(target) || !Number.isFinite(now)) return 0;
  return Math.max(0, Math.round((now - target) / 86_400_000));
}

/**
 * A row whose day has passed while the question it asks is still open. Today is
 * not late — it is still in the runway — so the comparison is strict.
 */
export function isOverdue(event: CalendarEvent, today: string = localDateKey()): boolean {
  return event.date < today && OVERDUE_KINDS.includes(event.kind);
}

export interface OverdueSlice {
  /** The oldest rows first, capped at the caller's limit. */
  items: CalendarEvent[];
  /** Every open past row, including the ones past the cap. */
  total: number;
}

/**
 * Epic 405 — what the runway cannot say. `upcomingEvents` keeps only rows on or
 * after today, so a follow-up that went due last week and was never answered
 * fell off the one card a reader checks in the morning. This fold puts those
 * rows back in front of them, oldest first: the one that has waited longest is
 * the one to answer first. The cap shortens the list, never the count.
 */
export function overdueEvents(
  events: CalendarEvent[],
  today: string = localDateKey(),
  limit: number = 5
): OverdueSlice {
  const late = events.filter((event) => isOverdue(event, today));
  late.sort((a, b) => a.date.localeCompare(b.date) || KIND_ORDER.indexOf(a.kind) - KIND_ORDER.indexOf(b.kind));
  const take = Math.max(0, Math.floor(limit));
  return { items: late.slice(0, take), total: late.length };
}

/**
 * Epic 393 — the runway, not just the next step. The card used to name one
 * row; a reader planning a week needs the next few. The list is already
 * sorted by `buildEvents`, so this is a slice, never a re-sort.
 */
export function upcomingEvents(
  events: CalendarEvent[],
  today: string = localDateKey(),
  limit: number = 5
): CalendarEvent[] {
  const take = Math.max(0, Math.floor(limit));
  return events.filter((event) => event.date >= today).slice(0, take);
}
