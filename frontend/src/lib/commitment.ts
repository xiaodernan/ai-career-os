/**
 * One line the reader said they'd own this week (Epic 228).
 *
 * The search is exhausting because it is open-ended; this card narrows it to
 * one sentence a week — the line they will be able to say out loud on Friday
 * ("I asked for the range", "I wrote the thank-you letter", "I told them
 * Friday"). Kept in this browser only, keyed by ISO week so it rotates
 * itself forward; surfaced on /offers and carried in the pocket. No
 * network, no scolding, nothing tracked.
 */

const PREFIX = "careeros.commitment.";
const MAX_LENGTH = 280;

function storage(): Storage | null {
  return typeof window === "undefined" ? null : window.localStorage;
}

export interface WeekCommitment {
  week: string;
  text: string;
}

/** ISO 8601 week label for a date, e.g. "2026-W46". */
export function isoWeekKey(date: Date = new Date()): string {
  // Standard ISO-weeks calculation: move to a target Thursday in the same ISO week.
  const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
  const day = d.getUTCDay() || 7;
  d.setUTCDate(d.getUTCDate() + 4 - day);
  const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
  const weekNo = Math.ceil(((d.getTime() - yearStart.getTime()) / 86_400_000 + 1) / 7);
  return `${d.getUTCFullYear()}-W${String(weekNo).padStart(2, "0")}`;
}

export function loadCommitment(replica: Storage | null = storage()): WeekCommitment {
  const week = isoWeekKey();
  if (!replica) return { week, text: "" };
  try {
    const raw = replica.getItem(PREFIX + week);
    if (!raw) return { week, text: "" };
    const parsed = JSON.parse(raw) as { text?: unknown } | null;
    return {
      week,
      text: typeof parsed?.text === "string" ? parsed.text.slice(0, MAX_LENGTH) : "",
    };
  } catch {
    return { week, text: "" };
  }
}

export function saveCommitment(
  text: string,
  replica: Storage | null = storage()
): WeekCommitment {
  const week = isoWeekKey();
  const trimmed = text.trim().slice(0, MAX_LENGTH);
  if (!replica) return { week, text: trimmed };
  try {
    replica.setItem(PREFIX + week, JSON.stringify({ text: trimmed }));
  } catch {
    // best effort — the visible state is the artifact; the reader owns it
  }
  return { week, text: trimmed };
}

export function clearCommitment(replica: Storage | null = storage()): void {
  const week = isoWeekKey();
  if (!replica) return;
  try {
    replica.removeItem(PREFIX + week);
  } catch {
    // ignore
  }
}

export const COMMITMENT_MAX_LENGTH = MAX_LENGTH;
