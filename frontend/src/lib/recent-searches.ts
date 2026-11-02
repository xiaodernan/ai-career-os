/**
 * The queries this browser has already run (52.3).
 *
 * Kept in localStorage rather than on the account: a search is a moment of a browser, not a fact
 * about the reader, and the palette must work before `/users/me` answers. The rules live here
 * instead of in the component so they can be exercised without a browser -- trim, drop anything
 * shorter than the palette's own two-character floor, fold case when comparing, newest first,
 * at most five.
 */
export const RECENT_SEARCH_LIMIT = 5;

const KEY = "careeros.recent-searches";

type Readable = Pick<Storage, "getItem">;
type Writable = Pick<Storage, "setItem">;

function defaultStorage(): (Readable & Writable) | undefined {
  return typeof window === "undefined" ? undefined : window.localStorage;
}

export function loadRecentSearches(from: Readable | undefined = defaultStorage()): string[] {
  if (!from) return [];
  try {
    const raw = from.getItem(KEY);
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed
      .filter((value): value is string => typeof value === "string" && value.trim().length >= 2)
      .slice(0, RECENT_SEARCH_LIMIT);
  } catch {
    // A half-written or hand-edited entry is not a reason to break the palette.
    return [];
  }
}

/** Adds one query to the front of the list and answers the list it wrote. */
export function rememberSearch(
  query: string,
  storage: (Readable & Writable) | undefined = defaultStorage()
): string[] {
  const term = query.trim();
  if (!storage || term.length < 2) return loadRecentSearches(storage);
  const kept = loadRecentSearches(storage).filter(
    (previous) => previous.toLowerCase() !== term.toLowerCase()
  );
  const next = [term, ...kept].slice(0, RECENT_SEARCH_LIMIT);
  try {
    storage.setItem(KEY, JSON.stringify(next));
  } catch {
    // Private mode refuses the write; the list still answers this visit.
  }
  return next;
}
