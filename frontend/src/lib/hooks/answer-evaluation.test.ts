import { describe, expect, it } from "vitest";

import { normalizeAnswerResponse } from "@/lib/hooks/actions";
import { normalizeInterviewReport } from "@/lib/api/normalize";

/**
 * The evaluator answers on a 0..1 scale — `EVAL_SYSTEM` in ai-service asks the model for
 * `"score": 0.0-1.0` and the LLM-failure fallback is `{"score": 0.5}` — while the runner badge
 * thresholds on 75/50 and prints "/100". Passing the raw float through therefore rendered an
 * excellent answer as "1/100" in red, and the neutral fallback as a failing grade. These tests
 * lock the coercion at the mapper and the agreement with the report path.
 */

/** One real POST /interview/sessions/{id}/answer body, field names from InterviewDtos.AnswerResponse. */
const payload = (evaluation: Record<string, unknown>) => ({
  candidateTurn: { id: "t1", seq: 2, role: "candidate", content: "I'd shard by tenant.", meta: null },
  followup: null,
  evaluation,
  next: { action: "followup", question: "How do you rebalance?", topic: "storage", difficulty: 0.6 },
  session: { id: "s1", status: "running" },
});

describe("normalizeAnswerResponse score scale", () => {
  it("turns the 0..1 evaluation into the 0..100 the badge draws", () => {
    const r = normalizeAnswerResponse(
      payload({ score: 0.82, strengths: ["Named the tradeoff"], weaknesses: [], missing_concepts: ["rebalancing"] })
    );
    expect(r.evaluation.score).toBe(82);
    expect(r.evaluation.missing).toEqual(["rebalancing"]);
  });

  it("reads the LLM-failure fallback as a neutral 50, not a failing 1", () => {
    // Exactly what ai-service returns when the evaluator call throws.
    expect(normalizeAnswerResponse(payload({ score: 0.5, question_was_answered: true })).evaluation.score).toBe(50);
  });

  it("leaves an already-percent score alone rather than scaling twice", () => {
    expect(normalizeAnswerResponse(payload({ score: 78 })).evaluation.score).toBe(78);
    expect(normalizeAnswerResponse(payload({ score: 1 })).evaluation.score).toBe(100);
  });

  it("reports no score when the payload carries none, so the badge hides", () => {
    // The reader guards on `typeof score === "number"`; 0 would pass that guard and print "0/100".
    const r = normalizeAnswerResponse(payload({ strengths: [] }));
    expect(r.evaluation.score).toBeUndefined();
  });

  it("scales the dimension map the same way the overall score is scaled", () => {
    const r = normalizeAnswerResponse(
      payload({ score: 0.8, dims: { technical_accuracy: 0.9, communication: 0.7 } })
    );
    expect(r.evaluation.dims).toEqual([
      { key: "technical_accuracy", label: "technical accuracy", score: 90 },
      { key: "communication", label: "communication", score: 70 },
    ]);
  });

  it("agrees with the report page about what a trajectory score means", () => {
    const trajectory = [
      { question: "Design a rate limiter", score: 0.86, depth: 2 },
      { question: "Why token bucket?", score: 0.44, depth: 1 },
    ];
    const live = normalizeAnswerResponse(payload({ score: 0.65, trajectory })).evaluation.trajectory;
    const report = normalizeInterviewReport({ overall: 0.65, trajectory_detail: trajectory });
    expect(live).toEqual(report!.trajectory);
    expect(live.map((t) => t.score)).toEqual([86, 44]);
  });

  it("maps the next move and stays null when there is none", () => {
    expect(normalizeAnswerResponse(payload({ score: 0.5 })).next).toMatchObject({
      question: "How do you rebalance?",
      topic: "storage",
    });
    expect(normalizeAnswerResponse({ evaluation: { score: 0.5 } }).next).toBeNull();
  });
});
