/**
 * The debrief (Epic 219) — the reader's own verdict on a rehearsal.
 *
 * The AI scores the session against its rubric; the coach's practice says the
 * reader should still write down, in their own words, what happened and what
 * they'll do differently — an after-action review nobody else gets to grade.
 * Like the decision ledger and the first-quarter plan, this is deliberately
 * browser-local: two textareas keyed per session id, no network, no server row.
 * The pure module is storage-injectable so the round trip is unit-testable.
 */

export interface DebriefState {
  whatHappened: string;
  differently: string;
}

const PREFIX = "careeros.debrief.";
export const DEBRIEF_STORAGE_PREFIX = PREFIX;

type StorageLike = Pick<Storage, "getItem" | "setItem" | "removeItem">;

function defaultStorage(): StorageLike | null {
  return typeof window === "undefined" ? null : window.localStorage;
}

const EMPTY: DebriefState = { whatHappened: "", differently: "" };

export function loadDebrief(sessionId: string, storage: StorageLike | null = defaultStorage()): DebriefState {
  if (!storage || !sessionId) return { ...EMPTY };
  try {
    const raw = storage.getItem(PREFIX + sessionId);
    if (!raw) return { ...EMPTY };
    const parsed = JSON.parse(raw) as Record<string, unknown>;
    return {
      whatHappened: typeof parsed.whatHappened === "string" ? parsed.whatHappened.slice(0, 4000) : "",
      differently: typeof parsed.differently === "string" ? parsed.differently.slice(0, 4000) : "",
    };
  } catch {
    return { ...EMPTY };
  }
}

export function saveDebrief(
  sessionId: string,
  state: DebriefState,
  storage: StorageLike | null = defaultStorage(),
): void {
  if (!storage || !sessionId) return;
  try {
    storage.setItem(PREFIX + sessionId, JSON.stringify({
      whatHappened: state.whatHappened.slice(0, 4000),
      differently: state.differently.slice(0, 4000),
    }));
  } catch {
    // best effort — the visible text stays regardless
  }
}

export function clearDebrief(sessionId: string, storage: StorageLike | null = defaultStorage()): void {
  if (!storage || !sessionId) return;
  try {
    storage.removeItem(PREFIX + sessionId);
  } catch {
    // ignore
  }
}

export function debriefIsEmpty(state: DebriefState): boolean {
  return state.whatHappened.trim().length === 0 && state.differently.trim().length === 0;
}
