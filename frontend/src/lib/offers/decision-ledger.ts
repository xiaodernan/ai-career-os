/**
 * The decision ledger (Epic 215) — the weights only the reader can set.
 *
 * The shelf ranks offers by one deterministic fact: total compensation. The
 * market can tell the reader which row is the most money; it cannot tell them
 * which row is the better life. The ledger is the reader's own ranking tool:
 * a short list of criteria (compensation, growth, team, mission, location,
 * stability — or ones nobody else thought of), a 0-5 weight on each, and a
 * 0-10 score per offer against each criterion. The weighted total is the
 * answer, computed client-side, persisted in the reader's browser, sent
 * nowhere.
 *
 * Deliberately local, like the first-quarter plan (Epic 209): the decision is
 * not search data, it is the reader's private reasoning made legible. Nothing
 * here reaches the network, and the module is written as pure functions over
 * plain state so the math can be tested without a browser.
 */

export interface LedgerCriterion {
  /** Stable id: a starter key ("comp"…) or "custom-<time>-<rand>". */
  id: string;
  /** True for criteria the reader wrote; their label is stored verbatim. */
  custom: boolean;
  /** Used only when `custom`; starters resolve their label through the locale. */
  label: string;
  /** 0-5. Zero means "not a factor for me" — it contributes nothing. */
  weight: number;
}

export interface LedgerState {
  criteria: LedgerCriterion[];
  /** scores[offerId][criterionId] = 0-10. A recorded 0 is a real score. */
  scores: Record<string, Record<string, number>>;
}

export interface LedgerRowResult {
  offerId: string;
  total: number;
  max: number;
  /** How many criteria have any recorded score for this offer. */
  scored: number;
}

export interface LedgerComputation {
  rows: LedgerRowResult[];
  /** Offer ids sharing the top total (1 normally, >1 on a genuine tie). Empty when nothing is scored or every weight is 0. */
  leaderIds: string[];
  /** Criteria length — every offer's row is scored against this many. */
  criterionCount: number;
}

export const LEDGER_STARTERS: ReadonlyArray<{ id: string; weight: number }> = [
  { id: "comp", weight: 5 },
  { id: "growth", weight: 4 },
  { id: "team", weight: 4 },
  { id: "mission", weight: 2 },
  { id: "location", weight: 3 },
  { id: "stability", weight: 3 },
];

export const LEDGER_MAX_CRITERIA = 8;
export const LEDGER_MAX_WEIGHT = 5;
export const LEDGER_MAX_SCORE = 10;

const STORAGE_KEY = "careeros.ledger.v1";

export function starterLedger(): LedgerState {
  return {
    criteria: LEDGER_STARTERS.map((s) => ({ id: s.id, custom: false, label: "", weight: s.weight })),
    scores: {},
  };
}

type StorageLike = Pick<Storage, "getItem" | "setItem" | "removeItem">;

function defaultStorage(): StorageLike | null {
  return typeof window === "undefined" ? null : window.localStorage;
}

function clampInt(value: unknown, min: number, max: number): number | null {
  const n = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(n)) return null;
  return Math.min(max, Math.max(min, Math.round(n)));
}

function sanitizeCriterion(raw: unknown): LedgerCriterion | null {
  if (!raw || typeof raw !== "object") return null;
  const c = raw as Record<string, unknown>;
  if (typeof c.id !== "string" || c.id.length === 0 || c.id.length > 64) return null;
  const weight = clampInt(c.weight, 0, LEDGER_MAX_WEIGHT) ?? 0;
  const custom = Boolean(c.custom);
  const label = typeof c.label === "string" ? c.label.slice(0, 120) : "";
  // A custom criterion with no words is a row the reader would not recognize.
  if (custom && label.trim().length === 0) return null;
  return { id: c.id, custom, label: custom ? label : "", weight };
}

function sanitize(raw: unknown): LedgerState {
  if (!raw || typeof raw !== "object") return starterLedger();
  const record = raw as Record<string, unknown>;

  const criteria: LedgerCriterion[] = [];
  const seen = new Set<string>();
  for (const item of Array.isArray(record.criteria) ? record.criteria : []) {
    const c = sanitizeCriterion(item);
    if (!c || seen.has(c.id)) continue;
    seen.add(c.id);
    criteria.push(c);
    if (criteria.length >= LEDGER_MAX_CRITERIA) break;
  }
  if (criteria.length === 0) return starterLedger();

  const scores: LedgerState["scores"] = {};
  const scoreRecord = record.scores;
  if (scoreRecord && typeof scoreRecord === "object" && !Array.isArray(scoreRecord)) {
    for (const [offerId, perCriterion] of Object.entries(scoreRecord as Record<string, unknown>)) {
      if (!perCriterion || typeof perCriterion !== "object" || Array.isArray(perCriterion)) continue;
      const kept: Record<string, number> = {};
      for (const [criterionId, value] of Object.entries(perCriterion as Record<string, unknown>)) {
        if (!seen.has(criterionId)) continue;
        const v = clampInt(value, 0, LEDGER_MAX_SCORE);
        if (v !== null) kept[criterionId] = v;
      }
      if (Object.keys(kept).length > 0) scores[offerId] = kept;
    }
  }

  return { criteria, scores };
}

export function loadLedger(storage: StorageLike | null = defaultStorage()): LedgerState {
  if (!storage) return starterLedger();
  try {
    const raw = storage.getItem(STORAGE_KEY);
    return raw ? sanitize(JSON.parse(raw)) : starterLedger();
  } catch {
    return starterLedger();
  }
}

export function saveLedger(state: LedgerState, storage: StorageLike | null = defaultStorage()): void {
  if (!storage) return;
  try {
    storage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch {
    // Best effort — the visible state still flips; the ledger just will not survive a reload.
  }
}

export function clearLedger(storage: StorageLike | null = defaultStorage()): void {
  if (!storage) return;
  try {
    storage.removeItem(STORAGE_KEY);
  } catch {
    // ignore
  }
}

export function addCriterion(state: LedgerState, label: string): LedgerState | null {
  const trimmed = label.trim().slice(0, 120);
  if (!trimmed) return null;
  if (state.criteria.length >= LEDGER_MAX_CRITERIA) return null;
  const id = `custom-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
  return {
    criteria: [...state.criteria, { id, custom: true, label: trimmed, weight: 3 }],
    scores: state.scores,
  };
}

export function removeCriterion(state: LedgerState, id: string): LedgerState {
  const criteria = state.criteria.filter((c) => c.id !== id);
  if (criteria.length === 0) return starterLedger();
  const scores: LedgerState["scores"] = {};
  for (const [offerId, perCriterion] of Object.entries(state.scores)) {
    const kept = { ...perCriterion };
    delete kept[id];
    if (Object.keys(kept).length > 0) scores[offerId] = kept;
  }
  return { criteria, scores };
}

export function setWeight(state: LedgerState, id: string, weight: number): LedgerState {
  const clamped = clampInt(weight, 0, LEDGER_MAX_WEIGHT);
  if (clamped === null) return state;
  return {
    ...state,
    criteria: state.criteria.map((c) => (c.id === id ? { ...c, weight: clamped } : c)),
  };
}

/** Set or clear one score. A blank/NaN score deletes the recorded cell. */
export function setScore(
  state: LedgerState,
  offerId: string,
  criterionId: string,
  score: string | number | null,
): LedgerState {
  const parsed =
    score === null || score === ""
      ? null
      : clampInt(score, 0, LEDGER_MAX_SCORE);
  const offerScores = { ...(state.scores[offerId] ?? {}) };
  if (parsed === null) {
    delete offerScores[criterionId];
  } else {
    offerScores[criterionId] = parsed;
  }
  const scores = { ...state.scores };
  if (Object.keys(offerScores).length === 0) {
    delete scores[offerId];
  } else {
    scores[offerId] = offerScores;
  }
  return { ...state, scores };
}

export function ledgerIsDirty(state: LedgerState): boolean {
  const defaults = starterLedger().criteria;
  if (state.criteria.some((c) => c.custom)) return true;
  if (state.criteria.length !== defaults.length) return true;
  for (const c of state.criteria) {
    const starter = defaults.find((d) => d.id === c.id);
    if (!starter || starter.weight !== c.weight) return true;
  }
  return Object.keys(state.scores).length > 0;
}

export function computeLedger(offerIds: string[], state: LedgerState): LedgerComputation {
  const { criteria } = state;
  const rows: LedgerRowResult[] = offerIds.map((offerId) => {
    let total = 0;
    let max = 0;
    let scored = 0;
    const perCriterion = state.scores[offerId] ?? {};
    for (const c of criteria) {
      max += c.weight * LEDGER_MAX_SCORE;
      const recorded = perCriterion[c.id];
      if (recorded !== undefined) {
        scored += 1;
        total += c.weight * recorded;
      }
    }
    return { offerId, total, max, scored };
  });

  const anyScored = rows.some((r) => r.scored > 0);
  if (!anyScored) {
    return { rows, leaderIds: [], criterionCount: criteria.length };
  }
  // Only rows the reader actually scored can lead — an untouched row would
  // otherwise inherit a crown from scores nobody gave it. And a crown only
  // exists when the weights separate something: a best of zero is not a signal.
  const candidates = rows.filter((r) => r.max > 0 && r.scored > 0);
  if (candidates.length === 0) {
    return { rows, leaderIds: [], criterionCount: criteria.length };
  }
  const best = Math.max(...candidates.map((r) => r.total));
  if (best <= 0) {
    return { rows, leaderIds: [], criterionCount: criteria.length };
  }
  return {
    rows,
    leaderIds: candidates.filter((r) => r.total === best).map((r) => r.offerId),
    criterionCount: criteria.length,
  };
}
