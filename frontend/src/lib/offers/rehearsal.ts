/**
 * The rehearsal room (Epic 227) — the ask, before the offer.
 *
 * The shelf compares offers by the market's arithmetic; the conversation that
 * follows the shelf is much harder, and this is the room to fumble it first.
 * Three hiring-manager pushes, three candidate replies each, a verdict at
 * nine. No model calls — the value of the exercise is in rehearsing the
 * reader's own craft, not in the machine's opinion of it. No claim here is
 * about this product; every push is the shape of a real salary negotiation.
 */

export interface RehearsalReply {
  id: string;
  /** 0 · cede · 1 · concede-with-a-move · 2 · hold · 3 · hold with evidence. */
  score: number;
}

export interface RehearsalPush {
  id: string;
  /** The manager's line — the shape the push actually takes. */
  replies: readonly RehearsalReply[];
}

export const REHEARSAL_PUSHES: readonly RehearsalPush[] = [
  {
    id: "band",
    replies: [
      { id: "hold", score: 3 },
      { id: "open", score: 2 },
      { id: "concede", score: 0 },
    ],
  },
  {
    id: "silence",
    replies: [
      { id: "clock", score: 3 },
      { id: "when", score: 2 },
      { id: "sure", score: 0 },
    ],
  },
  {
    id: "anchor",
    replies: [
      { id: "evidence", score: 3 },
      { id: "gap", score: 1 },
      { id: "maybe", score: 0 },
    ],
  },
];

const STORAGE_KEY = "careeros.rehearsal.v1";

export type RehearsalState = { scores: Record<string, string>; sentence: string };

export const EMPTY_REHEARSAL: RehearsalState = { scores: {}, sentence: "" };

const REP_SCORES: Record<string, number> = Object.fromEntries(
  REHEARSAL_PUSHES.flatMap((push) =>
    push.replies.map((reply) => [`${push.id}:${reply.id}`, reply.score])
  )
);

export function scoreOf(pushId: string, replyId: string): number {
  return REP_SCORES[`${pushId}:${replyId}`] ?? 0;
}

export function totalScore(state: RehearsalState): number {
  return Object.entries(state.scores).reduce(
    (sum, [pushId, replyId]) => sum + scoreOf(pushId, replyId),
    0
  );
}

export function answered(state: RehearsalState): boolean {
  return REHEARSAL_PUSHES.every((push) => push.id in state.scores);
}

export const MAX_REHEARSAL_SCORE = REHEARSAL_PUSHES.length * 3;

/** 9 — the verdict at the end of the walk. Keys are the bands the numbers keep. */
export function verdictBand(total: number): "none" | "weak" | "solid" | "strong" | "masterful" {
  if (total === 0) return "none";
  if (total <= 2) return "weak";
  if (total <= 5) return "solid";
  if (total <= 8) return "strong";
  return "masterful";
}

function storage(): Storage | null {
  return typeof window === "undefined" ? null : window.localStorage;
}

/** The stored state lives in this browser; nothing here is sent anywhere. */
export function loadRehearsal(replica: Storage | null = storage()): RehearsalState {
  if (!replica) return { ...EMPTY_REHEARSAL, scores: {} };
  try {
    const raw = replica.getItem(STORAGE_KEY);
    if (!raw) return { ...EMPTY_REHEARSAL, scores: {} };
    const parsed = JSON.parse(raw) as Partial<RehearsalState> | null;
    const scores =
      parsed?.scores && typeof parsed.scores === "object" && !Array.isArray(parsed.scores)
        ? Object.fromEntries(
            Object.entries(parsed.scores).filter(
              ([pushId, replyId]) =>
                typeof replyId === "string" &&
                REHEARSAL_PUSHES.some(
                  (push) => push.id === pushId && push.replies.some((r) => r.id === replyId)
                )
            )
          )
        : {};
    return {
      scores,
      sentence: typeof parsed?.sentence === "string" ? parsed.sentence.slice(0, 2000) : "",
    };
  } catch {
    return { ...EMPTY_REHEARSAL, scores: {} };
  }
}

export function saveRehearsal(
  state: RehearsalState,
  replica: Storage | null = storage()
): void {
  if (!replica) return;
  try {
    replica.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch {
    // best effort — the visible state is the honest artifact; the rehearsal
    // is the reader's, not the browser's
  }
}

export function clearRehearsal(replica: Storage | null = storage()): void {
  if (!replica) return;
  try {
    replica.removeItem(STORAGE_KEY);
  } catch {
    // ignore
  }
}
