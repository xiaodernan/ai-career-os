/**
 * The nine quests (Epic 235) — the dashboard's walking tour.
 *
 * Nine rooms in the same order the landing map draws (/resumes → /ceremony):
 * opening one checks its box in this browser. The tour is not a test and the
 * checks mean nothing to the server — they exist so a new reader learns the
 * product by walking it, at their own pace, in their own language. The state
 * lives in localStorage only; nothing here scores the person.
 */

export const TOUR_HREFS = [
  "/resumes",
  "/studio",
  "/growth",
  "/letters",
  "/interviews",
  "/applications",
  "/replies",
  "/offers",
  "/ceremony",
] as const;

export type TourRoute = (typeof TOUR_HREFS)[number];

const TOUR_KEY = "careeros.tour.v1";

function storage(): Storage | null {
  return typeof window === "undefined" ? null : window.localStorage;
}

function sanitize(visited: unknown): TourRoute[] {
  if (!Array.isArray(visited)) return [];
  const allowed = new Set<string>(TOUR_HREFS);
  return [...new Set(visited.filter((v): v is string => typeof v === "string" && allowed.has(v)))] as TourRoute[];
}

/** The saved visit set, filtered to the routes that belong to the tour. */
export function readTourVisits(replica: Storage | null = storage()): TourRoute[] {
  if (!replica) return [];
  try {
    const raw = replica.getItem(TOUR_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as { visited?: unknown } | null;
    return sanitize(parsed?.visited);
  } catch {
    return [];
  }
}

/** Mark a route visited. A route outside the tour is ignored, not stored. */
export function markTourVisited(
  route: string,
  replica: Storage | null = storage()
): TourRoute[] {
  if (!(TOUR_HREFS as readonly string[]).includes(route)) {
    return readTourVisits(replica);
  }
  const next = [...new Set([...readTourVisits(replica), route])] as TourRoute[];
  if (!replica) return next;
  try {
    replica.setItem(TOUR_KEY, JSON.stringify({ visited: next }));
  } catch {
    // best effort — the card re-reads the real list on the next render
  }
  return next;
}

export function clearTourVisits(replica: Storage | null = storage()): void {
  if (!replica) return;
  try {
    replica.removeItem(TOUR_KEY);
  } catch {
    // ignore
  }
}

export function tourProgress(visited: readonly string[]): { done: number; total: number } {
  const known = new Set(visited.filter((route) => (TOUR_HREFS as readonly string[]).includes(route)));
  return { done: known.size, total: TOUR_HREFS.length };
}
