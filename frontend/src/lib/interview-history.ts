/**
 * 67.1: the Q/A pairs a session already has, read from its own transcript.
 *
 * `GET /interview/sessions/{id}` answers with every turn -- interviewer rows and
 * candidate rows -- and the runner used to read only the last interviewer row
 * (the current question). Reloading mid-rehearsal therefore brought the question
 * back but not the transcript: the "this session so far" panel was empty, and
 * the question counter restarted at 1 although the server had three answered
 * turns. The rows are already in the payload; this is the fold from turns to the
 * pairs the panel draws.
 *
 * A pair is an interviewer row followed by a candidate row. A trailing
 * interviewer row is the question being asked now, not an answer; a candidate
 * row with no interviewer row before it (a partial write) is skipped rather
 * than paired with someone else's question. The score rides on the candidate
 * row's own `evaluation` map, and an unscored answer stays unscored.
 */

import { num, pick, rec, str } from "@/lib/api/normalize";

export interface AnsweredTurn {
  question: string;
  answer: string;
  score?: number;
}

export function answeredTurns(
  history: readonly unknown[] | null | undefined
): AnsweredTurn[] {
  const out: AnsweredTurn[] = [];
  let pendingQuestion: string | null = null;
  for (const row of history ?? []) {
    const role = str(row, "role");
    const content = str(row, "content") ?? "";
    if (role === "interviewer") {
      pendingQuestion = content;
      continue;
    }
    if (role !== "candidate" || pendingQuestion == null) continue;
    const evaluation = rec(pick(row, "evaluation"));
    const score = num(evaluation, "score");
    out.push({
      question: pendingQuestion,
      answer: content,
      ...(score != null ? { score } : {}),
    });
    pendingQuestion = null;
  }
  return out;
}
