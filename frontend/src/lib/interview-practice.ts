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
