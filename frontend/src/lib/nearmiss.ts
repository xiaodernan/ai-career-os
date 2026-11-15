/**
 * The near-miss (Epic 270) — the role that almost was.
 *
 * The not-yet letter holds one sentence about the no that arrived. This keeps the
 * one that almost landed — the near-offer, the final round that went to someone
 * else, the split-second proof you were almost whole on paper. Not a second shelf
 * of rejection letters: one role, named honestly, and what the miss taught the
 * reader. Local-only; nothing leaves the browser.
 *
 * Five slots make a near-miss complete — role, company, ask-again, learned, and
 * what changed since. None is required; the shelf is "sealed" when the role and
 * the learned line are both truthful (≥ 2 and ≥ 8 chars respectively).
 */

export const NEARMISS_PREFIX = "careeros.nearmiss.";

const LEARNED_MIN_CHARS = 8;
const ROLE_MIN_CHARS = 2;
const FIELD_MAX = 400;

export interface NearMissState {
  role: string;
  company: string;
  again: boolean | null;
  learned: string;
  changed: string;
  keptAt: string | null;
}

export function blankState(): NearMissState {
  return { role: "", company: "", again: null, learned: "", changed: "", keptAt: null };
}

const clamp = (value: unknown): string =>
  typeof value === "string" ? value.slice(0, FIELD_MAX) : "";

export function parseNearMiss(raw: string | null): NearMissState {
  const blank = blankState();
  if (!raw) return blank;
  try {
    const parsed = JSON.parse(raw) as Partial<NearMissState> | null;
    if (!parsed || typeof parsed !== "object") return blank;
    const again = parsed.again === true || parsed.again === false ? parsed.again : null;
    return {
      role: clamp(parsed.role).trim(),
      company: clamp(parsed.company).trim(),
      again,
      learned: clamp(parsed.learned).trim(),
      changed: clamp(parsed.changed).trim(),
      keptAt: typeof parsed.keptAt === "string" ? parsed.keptAt : null,
    };
  } catch {
    return blank;
  }
}

function defaultStorage(): Pick<Storage, "getItem" | "setItem" | "removeItem"> | null {
  return typeof window === "undefined" ? null : window.localStorage;
}

export function readNearMiss(storage: Pick<Storage, "getItem"> | null = defaultStorage()): NearMissState {
  if (!storage) return blankState();
  try {
    return parseNearMiss(storage.getItem(NEARMISS_PREFIX + "v1"));
  } catch {
    return blankState();
  }
}

export function writeNearMiss(state: NearMissState, storage: Pick<Storage, "setItem"> | null = defaultStorage()): void {
  if (!storage) return;
  try {
    storage.setItem(NEARMISS_PREFIX + "v1", JSON.stringify(state));
  } catch {
    /* best effort — visible state still flips */
  }
}

/** The five pieces a near-miss is made of, in the order the shelf walks them. */
export const NEARMISS_SLOTS = ["role", "company", "again", "learned", "changed"] as const;
export type NearMissSlot = (typeof NEARMISS_SLOTS)[number];

export function filledSlots(state: NearMissState): NearMissSlot[] {
  const filled: NearMissSlot[] = [];
  if (state.role.trim().length > 0) filled.push("role");
  if (state.company.trim().length > 0) filled.push("company");
  if (state.again !== null) filled.push("again");
  if (state.learned.trim().length > 0) filled.push("learned");
  if (state.changed.trim().length > 0) filled.push("changed");
  return filled;
}

export const SLOT_COUNT = 5;
export const SEALED_MIN = 2;

/** The shelf is sealed when the role and the honest lesson both exist — nothing else is asked. */
export function isSealed(state: NearMissState): boolean {
  return state.role.trim().length >= ROLE_MIN_CHARS && state.learned.trim().length >= LEARNED_MIN_CHARS;
}
