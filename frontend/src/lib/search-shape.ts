/**
 * 376: the shape of one reader's search, read off their own applications.
 *
 * Brief VI asks for "宏观史诗叙事 + 细节包罗万象", and the honest version of that on a
 * job search is a portrait: not "you applied to 12 jobs" but "your search was a burst
 * that lasted three weeks and then stopped". Two readers with the same count can have
 * completely different searches, and the count cannot tell them apart.
 *
 * Three measurements, each stated rather than derived, and each silent when its input
 * is absent: the span (first to last application), the busiest week, and the shape
 * name. Nothing here scores the reader -- a burst is not better or worse than a slow
 * burn, and the sentence says so.
 */

export interface ShapeInput {
  /** The reader's applications, as the board already holds them. */
  applications: Array<{ at?: string | null }>;
  /** "Now", injectable so a test can pin the clock. */
  now?: Date;
}

export type SearchShape = "single" | "burst" | "steady" | "long-tail" | "resting";

export interface SearchPortrait {
  /** How many applications the shape is read from. */
  count: number;
  /** Days from the first to the last application, inclusive. */
  spanDays: number | null;
  /** The busiest seven-day window, and how many applications landed in it. */
  busiest: { start: string; count: number } | null;
  shape: SearchShape;
}

const DAY_MS = 86_400_000;

/** Below this many applications there is no shape to read, only a count. */
export const SHAPE_MIN_COUNT = 3;

function dayIndex(value: string): number | null {
  const at = new Date(value).getTime();
  return Number.isFinite(at) ? Math.floor(at / DAY_MS) : null;
}

/**
 * The busiest seven-day window, found by walking the sorted days once.
 *
 * A fixed-width window over sorted timestamps is a two-pointer walk, not a scan of
 * every possible start: O(n) rather than O(n^2), which matters when a reader has
 * hundreds of applications.
 */
function busiestWeek(days: number[]): { start: string; count: number } | null {
  if (days.length === 0) return null;
  let best = 1;
  let bestStart = days[0];
  let left = 0;
  for (let right = 0; right < days.length; right += 1) {
    while (days[right] - days[left] >= 7) left += 1;
    const size = right - left + 1;
    if (size > best) {
      best = size;
      bestStart = days[left];
    }
  }
  return { start: new Date(bestStart * DAY_MS).toISOString(), count: best };
}

export function searchPortrait(input: ShapeInput): SearchPortrait {
  const stamps = input.applications
    .map((application) => application.at)
    .filter((at): at is string => typeof at === "string" && at.length > 0)
    .map(dayIndex)
    .filter((day): day is number => day !== null)
    .sort((a, b) => a - b);

  const count = stamps.length;
  if (count === 0) {
    return { count: 0, spanDays: null, busiest: null, shape: "resting" };
  }

  const spanDays = stamps[count - 1] - stamps[0] + 1;
  const busiest = busiestWeek(stamps);

  // A single application is a fact, not a shape; the sentence says so rather than
  // pretending one row is a pattern.
  if (count === 1) {
    return { count, spanDays, busiest, shape: "single" };
  }

  // A search that has not been touched in a long while is resting, not shaped: the
  // last application is old enough that the pattern is history rather than now.
  const now = input.now ? input.now.getTime() : Date.now();
  const daysSinceLast = Math.floor((now - stamps[count - 1] * DAY_MS) / DAY_MS);
  if (daysSinceLast > 60) {
    return { count, spanDays, busiest, shape: "resting" };
  }

  // Below the minimum there is not enough to call a shape; the sentence falls back
  // to the count and the span.
  if (count < SHAPE_MIN_COUNT) {
    return { count, spanDays, busiest, shape: "steady" };
  }

  const share = (busiest?.count ?? 0) / count;
  if (share >= 0.6) return { count, spanDays, busiest, shape: "burst" };
  if (spanDays >= 120) return { count, spanDays, busiest, shape: "long-tail" };
  return { count, spanDays, busiest, shape: "steady" };
}
