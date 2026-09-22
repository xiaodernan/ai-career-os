import { describe, expect, it } from "vitest";
import { normalizeRun, normalizeRunTrace, stepLabel, traceTotals } from "./activity-trace";

/** Fixtures copied from real rows in `agent_traces` (career chat run). */
const careerRun = {
  run: {
    id: "8f2f6a1c-6d1e-4f2a-9a1f-1b2c3d4e5f60",
    agent: "career",
    trigger: "chat",
    status: "completed",
    model: "mock-model",
    inputTokens: 498,
    outputTokens: 77,
    cachedTokens: 0,
    costUsd: 0,
    latencyMs: 1240,
    error: null,
    startedAt: "2026-09-21T19:15:22.185331Z",
    finishedAt: "2026-09-21T19:15:23.425331Z",
    rootRunId: null,
    conversationId: "c1",
  },
  traces: [
    { seq: 1, kind: "step_start", agent: "career", payload: { stage: "chat_turn" }, createdAt: "t1" },
    {
      seq: 2,
      kind: "llm_call",
      agent: "career",
      payload: {
        kind: "step_1",
        model: "mock-model",
        tools: ["search_resume"],
        cost_usd: 0,
        in_tokens: 249,
        latency_ms: 15,
        out_tokens: 1,
        text_preview: "",
      },
      createdAt: "t2",
    },
    {
      seq: 3,
      kind: "tool_call",
      agent: "career",
      payload: { args: { query: "experience projects skills" }, tool: "search_resume" },
      createdAt: "t3",
    },
    {
      seq: 4,
      kind: "tool_result",
      agent: "career",
      payload: { ok: true, tool: "search_resume", preview: '{"evidence":[]}' },
      createdAt: "t4",
    },
    { seq: 5, kind: "final", agent: "career", payload: { steps: 2, tools: ["search_resume"], answer_preview: "Here is what I found." }, createdAt: "t5" },
  ],
};

describe("activity trace mapping", () => {
  it("reads the run row from the {run, traces} envelope", () => {
    const run = normalizeRun(careerRun);
    expect(run).toMatchObject({
      id: "8f2f6a1c-6d1e-4f2a-9a1f-1b2c3d4e5f60",
      agent: "career",
      trigger: "chat",
      status: "completed",
      inputTokens: 498,
      outputTokens: 77,
      latencyMs: 1240,
    });
  });

  it("accepts a bare run object too", () => {
    expect(normalizeRun(careerRun.run).agent).toBe("career");
  });

  it("labels every step from its persisted payload", () => {
    const { steps } = normalizeRunTrace(careerRun);
    expect(steps.map((s) => s.label)).toEqual([
      "chat_turn",
      "step_1 · mock-model",
      "search_resume",
      "search_resume result",
      "Here is what I found.",
    ]);
  });

  it("keeps latency and payload so the timeline can expand real data", () => {
    const { steps } = normalizeRunTrace(careerRun);
    const llm = steps.find((s) => s.kind === "llm_call");
    expect(llm?.durationMs).toBe(15);
    expect(llm?.payload).toMatchObject({ in_tokens: 249, out_tokens: 1 });
    expect(steps.find((s) => s.kind === "tool_result")?.status).toBe("ok");
  });

  it("marks a failed tool result and the last step of a failed run", () => {
    const failed = {
      run: { id: "r", agent: "career", status: "failed", error: "upstream 502" },
      traces: [
        { seq: 1, kind: "tool_result", payload: { ok: false, tool: "search_jobs", error: "timeout" } },
        { seq: 2, kind: "final", payload: { answer_preview: "aborted" } },
      ],
    };
    const { steps } = normalizeRunTrace(failed);
    expect(steps[0].status).toBe("error");
    expect(steps[1].status).toBe("error");
  });

  it("rolls totals up from the run, falling back to step payloads", () => {
    expect(traceTotals(normalizeRunTrace(careerRun))).toMatchObject({
      tokens: 575,
      toolCalls: 1,
      llmCalls: 1,
      failedSteps: 0,
    });
    const noRunCounters = normalizeRunTrace({
      run: { id: "r", agent: "career", status: "completed", inputTokens: 0, outputTokens: 0, costUsd: 0 },
      traces: [{ seq: 1, kind: "llm_call", payload: { in_tokens: 40, out_tokens: 8, cost_usd: 0.002 } }],
    });
    expect(traceTotals(noRunCounters)).toMatchObject({ tokens: 48, costUsd: 0.002, llmCalls: 1 });
  });

  it("never invents a label or hides an unknown kind", () => {
    expect(stepLabel("step_start", {})).toBe("Run started");
    const unknown = normalizeRunTrace({
      run: { id: "r" },
      traces: [{ seq: 1, kind: "quantum_leap", payload: { note: "x" } }],
    });
    expect(unknown.steps[0].kind).toBe("step_start");
    expect(unknown.steps[0].label).toBe("Run started");
  });

  it("survives an empty or malformed response", () => {
    for (const raw of [null, undefined, {}, { run: null, traces: null }, "nope"]) {
      const trace = normalizeRunTrace(raw);
      expect(trace.steps).toEqual([]);
      expect(traceTotals(trace)).toMatchObject({ tokens: undefined, toolCalls: 0 });
    }
  });
});
