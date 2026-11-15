/**
 * The not-yet letter (Epic 237) — the door nobody writes down.
 *
 * Every recruiter's no is a letter a real person read yours and then wrote.
 * Three shapes they actually write. The module is not a game and not a
 * score: three doors, each with the honest decode of the shape, and one
 * sentence the reader keeps — the same kept-sentence contract the debrief
 * and the ledger use. Local-only, nothing here is sent anywhere.
 */

export const NOT_YET_DOORS = [
  { id: "calibrate" },
  { id: "hold" },
  { id: "impress" },
] as const;

export type NotYetDoor = (typeof NOT_YET_DOORS)[number]["id"];

const STORAGE_KEY = "careeros.notyet.v1";
const MAX_SENTENCE = 1000;

function storage(): Storage | null {
  return typeof window === "undefined" ? null : window.localStorage;
}

export interface NotYetState {
  sentence: string;
}

export const EMPTY_NOT_YET: NotYetState = { sentence: "" };

/** The kept sentence lives in this browser; nothing here is sent anywhere. */
export function loadNotYet(replica: Storage | null = storage()): NotYetState {
  if (!replica) return { ...EMPTY_NOT_YET };
  try {
    const raw = replica.getItem(STORAGE_KEY);
    if (!raw) return { ...EMPTY_NOT_YET };
    const parsed = JSON.parse(raw) as Partial<NotYetState> | null;
    return {
      sentence: typeof parsed?.sentence === "string" ? parsed.sentence.slice(0, MAX_SENTENCE) : "",
    };
  } catch {
    return { ...EMPTY_NOT_YET };
  }
}

export function saveNotYet(
  sentence: string,
  replica: Storage | null = storage()
): NotYetState {
  const trimmed = sentence.slice(0, MAX_SENTENCE);
  if (!replica) return { sentence: trimmed };
  try {
    replica.setItem(STORAGE_KEY, JSON.stringify({ sentence: trimmed }));
  } catch {
    // best effort — the visible state is the honest artifact; the kept
    // sentence belongs to the reader, not the browser
  }
  return { sentence: trimmed };
}

export function clearNotYet(replica: Storage | null = storage()): void {
  if (!replica) return;
  try {
    replica.removeItem(STORAGE_KEY);
  } catch {
    // ignore
  }
}

export const NOT_YET_MAX_LENGTH = MAX_SENTENCE;
