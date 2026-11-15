/**
 * The room you walk into (Epic 268) — the pre-interview research kit.
 *
 * The company page tells the reader what the company IS. This keeps the
 * reader's own thinking about the room they are about to knock on — five
 * lenses, written in the reader's own words, never leaving the browser.
 * The data is authored here because it is the reader's *prep*, which is
 * exactly the class of thing `careeros.*` pockets exist for: no research,
 * no claim, no sentence the reader did not write.
 *
 * The five lenses (in the order they should be attacked):
 *
 *   money   — how the room makes money, and what has to be true for it to keep working
 *   role    — the real scope: team shape, reporting line, what you own by month three
 *   year    — the last twelve months: what shipped, what slipped, what changed at the top
 *   proof   — the thinnest joint in *your own* story, named plainly
 *   bet     — the honest human layer: why *this* room, not a better-named one
 *
 * The module is pure: an injectable storage port, JSON that tolerates
 * corruption by reading as blank, and one derivation worth having out loud —
 * which two lenses the kit proposes to turn into questions for the room.
 */

export const PREREAD_PREFIX = "careeros.preread.";

export const LENS_IDS = ["money", "role", "year", "proof", "bet"] as const;
export type LensId = (typeof LENS_IDS)[number];

export type PrereadLevel = 0 | 1 | 2;

export interface PrereadState {
  notes: Record<LensId, string>;
  levels: Record<LensId, PrereadLevel>;
  /** ISO instant the reader last kept an edit, or null when nothing was kept yet. */
  keptAt: string | null;
}

export const MAX_TOTAL = 10;
export const READY_TOTAL = 8;

/** Preference order for the two questions the synthesis proposes: context first, position second. */
export const SYNTHESIS_ORDER: readonly LensId[] = ["year", "role", "money", "proof", "bet"];

export function blankState(): PrereadState {
  const notes = {} as Record<LensId, string>;
  const levels = {} as Record<LensId, PrereadLevel>;
  for (const id of LENS_IDS) {
    notes[id] = "";
    levels[id] = 0;
  }
  return { notes, levels, keptAt: null };
}

function asLevel(value: unknown): PrereadLevel {
  return value === 1 ? 1 : value === 2 ? 2 : 0;
}

/** Corruption reads as blank — a reader who pasted JSON over their notes gets an empty kit, never an exception. */
export function parsePreread(raw: string | null): PrereadState {
  const blank = blankState();
  if (!raw) return blank;
  try {
    const parsed = JSON.parse(raw) as Partial<PrereadState> | null;
    if (!parsed || typeof parsed !== "object") return blank;
    const notes = { ...blank.notes, ...(parsed.notes ?? {}) };
    const levels = { ...blank.levels, ...(parsed.levels ?? {}) };
    for (const id of LENS_IDS) {
      notes[id] = typeof notes[id] === "string" ? notes[id] : "";
      levels[id] = asLevel(levels[id]);
    }
    return {
      notes,
      levels,
      keptAt: typeof parsed.keptAt === "string" ? parsed.keptAt : null,
    };
  } catch {
    return blank;
  }
}

function defaultStorage(): Pick<Storage, "getItem" | "setItem" | "removeItem"> | null {
  return typeof window === "undefined" ? null : window.localStorage;
}

export function readPreread(companyId: string, storage: Pick<Storage, "getItem"> | null = defaultStorage()): PrereadState {
  if (!storage || !companyId) return blankState();
  try {
    return parsePreread(storage.getItem(PREREAD_PREFIX + companyId));
  } catch {
    return blankState();
  }
}

export function writePreread(
  companyId: string,
  state: PrereadState,
  storage: Pick<Storage, "setItem"> | null = defaultStorage(),
): void {
  if (!storage || !companyId) return;
  try {
    storage.setItem(PREREAD_PREFIX + companyId, JSON.stringify(state));
  } catch {
    /* best effort — visible state still flips; the reader never sees a failure for their own prep */
  }
}

export function levelTotal(state: Pick<PrereadState, "levels">): number {
  return LENS_IDS.reduce((sum, id) => sum + state.levels[id], 0);
}

export function readyForSynthesis(state: Pick<PrereadState, "levels" | "notes">): boolean {
  if (levelTotal(state) < READY_TOTAL) return false;
  return synthesisLenses(state, 2).length >= 2;
}

/**
 * Which lenses the two questions should be built from: the first two with words in
 * the reader's own voice, in the SYNTHESIS_ORDER preference. Notes is the reader's
 * voice; levels only gate readiness, never the quote.
 */
export function synthesisLenses(state: Pick<PrereadState, "notes">, limit = 2): LensId[] {
  const picked: LensId[] = [];
  for (const id of SYNTHESIS_ORDER) {
    if (picked.length >= limit) break;
    const text = state.notes[id].trim();
    if (text.length >= 8) picked.push(id);
  }
  return picked;
}
