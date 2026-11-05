import { describe, expect, it } from "vitest";

import { answeredTurns } from "./interview-history";

const history = [
  { role: "interviewer", content: "Walk me through your last migration." },
  { role: "candidate", content: "We moved 4 TB off a single primary.", evaluation: { score: 71 } },
  { role: "interviewer", content: "What broke first?" },
  { role: "candidate", content: "The replication lag alert.", evaluation: { score: "64" } },
  { role: "interviewer", content: "Why did you choose that order?" },
];

describe("answeredTurns", () => {
  it("pairs each interviewer row with the candidate row under it", () => {
    const turns = answeredTurns(history);
    expect(turns).toHaveLength(2);
    expect(turns[0]).toEqual({
      question: "Walk me through your last migration.",
      answer: "We moved 4 TB off a single primary.",
      score: 71,
    });
  });

  it("leaves the question being asked now out of the transcript", () => {
    // The trailing interviewer row is the runner's current question; counting it
    // as an answered turn would make the counter and the panel disagree.
    const turns = answeredTurns(history);
    expect(turns.map((t) => t.question)).not.toContain("Why did you choose that order?");
  });

  it("keeps the score the server wrote, including one that arrived as a string", () => {
    expect(answeredTurns(history)[1].score).toBe(64);
    expect(answeredTurns([{ role: "interviewer", content: "Q" },
      { role: "candidate", content: "A" }])[0].score).toBeUndefined();
  });

  it("skips a candidate row with no question above it rather than borrowing one", () => {
    const turns = answeredTurns([
      { role: "candidate", content: "orphan", evaluation: { score: 40 } },
      { role: "interviewer", content: "Q1" },
      { role: "candidate", content: "A1" },
    ]);
    expect(turns).toEqual([{ question: "Q1", answer: "A1" }]);
  });

  it("answers an empty list for a session with no turns", () => {
    expect(answeredTurns(undefined)).toEqual([]);
    expect(answeredTurns([])).toEqual([]);
  });
});
