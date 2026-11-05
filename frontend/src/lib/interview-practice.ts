/**
 * 59.1: what the rehearsals around this one say.
 *
 * A report is one sitting, but the reader's question is usually "is this getting
 * better?". The card's rehearsals are already one list (57.1), so the answer is
 * a fold over that list rather than a new read: where this session sits in the
 * history, how many there are, and the best score any of them earned.
 *
 * The scores are the frontend's 0-100 (`mapInterviewSessionItem` scales the
 * stored fraction once), so `best` is compared and printed on the same scale.
 */

export interface PracticeSession {
  id: string;
  overall?: number | null;
  startedAt?: string;
  /** Only a `completed` sibling has a report to brief the next attempt from (62.1). */
  status?: string;
}

export interface PracticeLine {
  /** 1-based position in the card's history, oldest first. */
  position: number;
  /** How many rehearsals the card has, including this one. */
  count: number;
  /** The best graded score among them, when at least one was graded. */
  best?: number;
}

/**
 * The line for `currentId`, or null when the session is not in the list it was
 * measured against -- a free rehearsal, or a narrowed page that did not reach
 * this old session. Not finding it is a reason to say nothing, not to place it
 * at the newest end and claim a position the page cannot see.
 */
export function cardPractice(
  sessions: readonly PracticeSession[],
  currentId: string | null | undefined
): PracticeLine | null {
  if (!currentId || sessions.length === 0) return null;
  const ordered = [...sessions].sort((a, b) =>
    (a.startedAt ?? "").localeCompare(b.startedAt ?? "")
  );
  const at = ordered.findIndex((s) => s.id === currentId);
  if (at < 0) return null;
  const graded = ordered
    .map((s) => s.overall)
    .filter((score): score is number => typeof score === "number");
  return {
    position: at + 1,
    count: ordered.length,
    ...(graded.length > 0 ? { best: Math.max(...graded) } : {}),
  };
}

/**
 * 62.1: the last finished rehearsal on this card, other than the one being taken.
 *
 * A retry starts from nothing today: the new session is built fresh, so whatever
 * the previous report said to fix is only visible by leaving the page. The card's
 * list already holds every sibling; this picks the newest `completed` one, which
 * is the one whose report the runner can read for its gaps. Newest first by
 * `startedAt`, ties broken by id so the choice cannot flap between renders.
 */
export function previousRehearsal(
  sessions: readonly PracticeSession[],
  currentId: string | null | undefined
): PracticeSession | null {
  if (!currentId) return null;
  const finished = sessions
    .filter((s) => s.id !== currentId && s.status === "completed")
    .sort((a, b) => {
      const byStart = (b.startedAt ?? "").localeCompare(a.startedAt ?? "");
      return byStart !== 0 ? byStart : a.id.localeCompare(b.id);
    });
  return finished[0] ?? null;
}

/**
 * 62.2: this sitting's score read against the one it followed.
 *
 * The practice line answers "where am I in the history"; this answers "did the
 * retry move it". Both numbers come from rows the page already has, and either
 * one missing -- an ungraded sitting, a card with no earlier report -- means
 * there is nothing to compare rather than a zero to show.
 */
export interface ScoreDelta {
  previous: number;
  current: number;
  delta: number;
}

export function scoreDelta(
  previous: number | null | undefined,
  current: number | null | undefined
): ScoreDelta | null {
  if (previous == null || current == null) return null;
  if (!Number.isFinite(previous) || !Number.isFinite(current)) return null;
  return { previous, current, delta: current - previous };
}
