import { describe, expect, it } from "vitest";

import { mapInterviewSessionDetail, mapInterviewSessionItem } from "@/lib/hooks/resources";

/**
 * One row of GET /interview/sessions, field-for-field from
 * InterviewDtos.SessionItem{id,jobId,jdId,resumeVersionId,companyName,positionTitle,
 * mode,status,difficulty,config,startedAt,finishedAt}.
 */
const SESSION_ITEM = {
  id: "55555555-0000-0000-0000-000000000005",
  jobId: "11111111-0000-0000-0000-000000000000",
  jdId: null,
  resumeVersionId: null,
  companyName: "ACME GmbH",
  positionTitle: "Staff Backend Engineer",
  mode: "technical",
  status: "completed",
  difficulty: 3.5,
  config: { focus: "concurrency" },
  startedAt: "2026-09-01T10:00:00Z",
  finishedAt: "2026-09-01T10:22:00Z",
};

describe("mapInterviewSessionItem", () => {
  it("reads the role off the key the backend actually sends", () => {
    // The UI renders `jobTitle` on three screens; the alias list never included the
    // wire name `positionTitle`, so the role was dropped for every session.
    expect(mapInterviewSessionItem(SESSION_ITEM).jobTitle).toBe("Staff Backend Engineer");
  });

  it("maps the remaining scalars", () => {
    expect(mapInterviewSessionItem(SESSION_ITEM)).toMatchObject({
      id: "55555555-0000-0000-0000-000000000005",
      jobId: "11111111-0000-0000-0000-000000000000",
      companyName: "ACME GmbH",
      mode: "technical",
      status: "completed",
      difficulty: 3.5,
      startedAt: "2026-09-01T10:00:00Z",
      finishedAt: "2026-09-01T10:22:00Z",
    });
  });

  it("keeps the mock-mode defaults when the row is sparse", () => {
    expect(mapInterviewSessionItem({ id: "s-1" })).toMatchObject({
      id: "s-1",
      mode: "mixed",
      status: "active",
      jobTitle: null,
    });
  });
});

describe("mapInterviewSessionDetail", () => {
  const DETAIL = {
    session: SESSION_ITEM,
    turns: [
      { id: "t1", seq: 1, role: "user", content: "I used an index.", questionMeta: null },
      {
        id: "t2",
        seq: 2,
        role: "assistant",
        content: "Why did the planner still choose a seq scan?",
        questionMeta: { topic: "planning", difficulty: 4 },
      },
    ],
    evaluation: { id: "e1", dims: { depth: 70 }, summary: { overall: 66 } },
  };

  it("takes scalars from the nested session node", () => {
    const got = mapInterviewSessionDetail(DETAIL, "55555555-0000-0000-0000-000000000005");
    expect(got.jobTitle).toBe("Staff Backend Engineer");
    expect(got.companyName).toBe("ACME GmbH");
    expect(got.status).toBe("completed");
  });

  it("keeps turns and evaluation as siblings of session", () => {
    const got = mapInterviewSessionDetail(DETAIL, "x");
    expect(got.history).toHaveLength(2);
    expect(got.report).toEqual({ id: "e1", dims: { depth: 70 }, summary: { overall: 66 } });
    // SessionItem has no questionCount, so the turn count is the only honest number.
    expect(got.questionCount).toBe(2);
  });

  it("derives the pending question from the last assistant turn", () => {
    const got = mapInterviewSessionDetail(DETAIL, "x");
    expect(got.currentQuestion).toMatchObject({
      text: "Why did the planner still choose a seq scan?",
      topic: "planning",
      difficulty: 4,
    });
  });

  it("falls back to the payload itself when there is no session wrapper", () => {
    const got = mapInterviewSessionDetail(SESSION_ITEM, "x");
    expect(got.jobTitle).toBe("Staff Backend Engineer");
    expect(got.id).toBe(SESSION_ITEM.id);
  });

  it("prefers the route id over a missing payload id", () => {
    expect(mapInterviewSessionDetail({ turns: [] }, "route-id").id).toBe("route-id");
  });
});
