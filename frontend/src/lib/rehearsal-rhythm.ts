/**
 * 374: how long it has been since the reader last rehearsed.
 *
 * Brief VI asks for "新的后续环节" and for a world that keeps giving. A rehearsal is a
 * skill, and a skill goes stale: the reader who took four in October and none since
 * is not lazy, they are simply out of the habit -- and nothing on the list said so.
 * The list shows what happened; this says what has NOT happened lately.
 *
 * Pure and total: an empty ledger, an unparseable date or a clock in the future all
 * answer honestly rather than a number. The thresholds are stated in days because
 * that is the unit a reader thinks in, and the sentence is the reader's own data
 * (the date of the last rehearsal), never an invented one.
 */

export interface RhythmInput {
  /** The sessions the list already holds; only the timestamps are read. */
  sessions: Array<{ at?: string | null }>;
  /** "Now", injectable so a test can pin the clock. */
  now?: Date;
}

export interface Rhythm {
  /** Days since the last rehearsal, rounded down. Null when there has never been one. */
  daysSince: number | null;
  /** The last rehearsal's own date, for the sentence. */
  lastAt: string | null;
  /**
   * How stale the habit is. `none` is a reader who has never rehearsed (not a
   * criticism -- they have not started), `fresh` is inside a week, `warm` inside a
   * month, `stale` beyond it. The bands are the product's, stated rather than
   * derived, so the sentence is the same on every install.
   */
  band: "none" | "fresh" | "warm" | "stale";
}

const DAY_MS = 86_400_000;

/** The bands, in days, stated once so a sentence and a test read the same rule. */
export const RHYTHM_BANDS = { fresh: 7, warm: 30 } as const;

function parse(value: string | null | undefined): number | null {
  if (!value) return null;
  const at = new Date(value).getTime();
  return Number.isFinite(at) ? at : null;
}

export function rehearsalRhythm(input: RhythmInput): Rhythm {
  const stamps = input.sessions
    .map((session) => parse(session.at))
    .filter((at): at is number => at !== null);

  if (stamps.length === 0) {
    return { daysSince: null, lastAt: null, band: "none" };
  }

  const last = Math.max(...stamps);
  const now = input.now ? input.now.getTime() : Date.now();
  const daysSince = Math.max(0, Math.floor((now - last) / DAY_MS));
  const band =
    daysSince <= RHYTHM_BANDS.fresh
      ? "fresh"
      : daysSince <= RHYTHM_BANDS.warm
        ? "warm"
        : "stale";

  // The reader's own timestamp, carried through untouched so the sentence can
  // name the day rather than a derived number.
  const raw = input.sessions
    .map((session) => session.at)
    .find((at): at is string => typeof at === "string" && new Date(at).getTime() === last);

  return { daysSince, lastAt: raw ?? new Date(last).toISOString(), band };
}
