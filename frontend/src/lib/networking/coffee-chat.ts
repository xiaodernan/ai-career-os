/**
 * The first coffee (Epic 230) — the conversation before the referral.
 *
 * A coffee chat is fifteen minutes with one person who can open one door;
 * the registry remembers who they are, this room rehearses the room itself.
 * Three moments — the ask, the middle, the close — three replies each, a
 * verdict at nine. No model calls: the value is in the reader's craft, not
 * the machine's opinion of it. Every push is the shape a real networking
 * chat takes, and every verdict is a mirror, not advice. The chosen
 * sentence lives in this browser only, like the rehearsal room and the
 * decision ledger.
 */

export interface CoffeeReply {
  id: string;
  /** 0 · burdens or deflects · 1 · safe but inert · 3 · specific, finite, warm. */
  score: number;
}

export interface CoffeeMoment {
  id: string;
  replies: readonly CoffeeReply[];
}

export const COFFEE_MOMENTS: readonly CoffeeMoment[] = [
  {
    id: "ask",
    replies: [
      { id: "burden", score: 0 },
      { id: "generic", score: 1 },
      { id: "specific", score: 3 },
    ],
  },
  {
    id: "middle",
    replies: [
      { id: "nothing", score: 0 },
      { id: "recap", score: 1 },
      { id: "lead", score: 3 },
    ],
  },
  {
    id: "close",
    replies: [
      { id: "thanks", score: 0 },
      { id: "loop", score: 1 },
      { id: "forward", score: 3 },
    ],
  },
];

const STORAGE_KEY = "careeros.coffeechat.v1";

export type CoffeeChatState = { scores: Record<string, string>; sentence: string };

export const EMPTY_COFFEE_CHAT: CoffeeChatState = { scores: {}, sentence: "" };

const REPLY_SCORES: Record<string, number> = Object.fromEntries(
  COFFEE_MOMENTS.flatMap((moment) =>
    moment.replies.map((reply) => [`${moment.id}:${reply.id}`, reply.score])
  )
);

export function coffeeScoreOf(momentId: string, replyId: string): number {
  return REPLY_SCORES[`${momentId}:${replyId}`] ?? 0;
}

export function coffeeTotalScore(state: CoffeeChatState): number {
  return Object.entries(state.scores).reduce(
    (sum, [momentId, replyId]) => sum + coffeeScoreOf(momentId, replyId),
    0
  );
}

export function coffeeAnswered(state: CoffeeChatState): boolean {
  return COFFEE_MOMENTS.every((moment) => moment.id in state.scores);
}

export const MAX_COFFEE_SCORE = COFFEE_MOMENTS.length * 3;

/** The verdict at the end of the walk. Keys are the bands the numbers keep. */
export function coffeeVerdictBand(
  total: number
): "none" | "weak" | "solid" | "strong" | "masterful" {
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
export function loadCoffeeChat(replica: Storage | null = storage()): CoffeeChatState {
  if (!replica) return { ...EMPTY_COFFEE_CHAT, scores: {} };
  try {
    const raw = replica.getItem(STORAGE_KEY);
    if (!raw) return { ...EMPTY_COFFEE_CHAT, scores: {} };
    const parsed = JSON.parse(raw) as Partial<CoffeeChatState> | null;
    const scores =
      parsed?.scores && typeof parsed.scores === "object" && !Array.isArray(parsed.scores)
        ? Object.fromEntries(
            Object.entries(parsed.scores).filter(
              ([momentId, replyId]) =>
                typeof replyId === "string" &&
                COFFEE_MOMENTS.some(
                  (moment) =>
                    moment.id === momentId && moment.replies.some((r) => r.id === replyId)
                )
            )
          )
        : {};
    return {
      scores,
      sentence: typeof parsed?.sentence === "string" ? parsed.sentence.slice(0, 2000) : "",
    };
  } catch {
    return { ...EMPTY_COFFEE_CHAT, scores: {} };
  }
}

export function saveCoffeeChat(
  state: CoffeeChatState,
  replica: Storage | null = storage()
): void {
  if (!replica) return;
  try {
    replica.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch {
    // best effort — the visible state is the honest artifact; the chat
    // belongs to the reader, not the browser
  }
}

export function clearCoffeeChat(replica: Storage | null = storage()): void {
  if (!replica) return;
  try {
    replica.removeItem(STORAGE_KEY);
  } catch {
    // ignore
  }
}
