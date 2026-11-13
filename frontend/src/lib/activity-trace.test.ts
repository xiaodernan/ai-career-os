import { describe, expect, it } from "vitest";
import { normalizeRun, normalizeRunTrace, stepLabel, traceTotals } from "./activity-trace";
import { fill, lookup } from "@/lib/i18n/locale-context";
import { translations, type Locale } from "@/lib/i18n/translations";
import { TRACE_KINDS } from "@/lib/trace-kinds";
import { traceKindWord } from "@/lib/status-words";

function tFor(locale: Locale) {
  return (key: string, vars?: Record<string, string | number>): string => {
    const raw = lookup(translations[locale], key);
    return raw == null ? key : fill(raw, vars);
  };
}

const en = tFor("en");
const zh = tFor("zh");

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
        mode: "stream",
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
    const { steps } = normalizeRunTrace(en, careerRun);
    expect(steps.map((s) => s.label)).toEqual([
      "chat_turn",
      "step_1 · mock-model · stream",
      "search_resume",
      "search_resume result",
      "Here is what I found.",
    ]);
  });

  it("a trace without mode still labels without the trailing answer-path word", () => {
    expect(stepLabel(en, "llm_call", { kind: "step_1", model: "mock-model" }))
      .toBe("step_1 · mock-model");
    expect(stepLabel(zh, "llm_call", { kind: "step_1", model: "mock-model", mode: "stream" }))
      .toBe("step_1 · mock-model · stream");
  });

  it("keeps latency and payload so the timeline can expand real data", () => {
    const { steps } = normalizeRunTrace(en, careerRun);
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
    const { steps } = normalizeRunTrace(en, failed);
    expect(steps[0].status).toBe("error");
    expect(steps[1].status).toBe("error");
  });

  it("rolls totals up from the run, falling back to step payloads", () => {
    expect(traceTotals(normalizeRunTrace(en, careerRun))).toMatchObject({
      tokens: 575,
      toolCalls: 1,
      llmCalls: 1,
      failedSteps: 0,
    });
    const noRunCounters = normalizeRunTrace(en, {
      run: { id: "r", agent: "career", status: "completed", inputTokens: 0, outputTokens: 0, costUsd: 0 },
      traces: [{ seq: 1, kind: "llm_call", payload: { in_tokens: 40, out_tokens: 8, cost_usd: 0.002 } }],
    });
    expect(traceTotals(noRunCounters)).toMatchObject({ tokens: 48, costUsd: 0.002, llmCalls: 1 });
  });

  it("never invents a label or hides an unknown kind", () => {
    expect(stepLabel(en, "step_start", {})).toBe("Step start");
    expect(stepLabel(zh, "step_start", {})).toBe("步骤开始");
    const unknown = normalizeRunTrace(en, {
      run: { id: "r" },
      traces: [{ seq: 1, kind: "quantum_leap", payload: { note: "x" } }],
    });
    expect(unknown.steps[0].kind).toBe("step_start");
    expect(unknown.steps[0].label).toBe("Step start");
  });

  it("survives an empty or malformed response", () => {
    for (const raw of [null, undefined, {}, { run: null, traces: null }, "nope"]) {
      const trace = normalizeRunTrace(en, raw);
      expect(trace.steps).toEqual([]);
      expect(traceTotals(trace)).toMatchObject({ tokens: undefined, toolCalls: 0 });
    }
  });
});

/**
 * The line a step shows when its payload carries no text of its own.
 *
 * The mapper wrote that line itself: nine English phrases, rendered beside the
 * badge the timeline had already put in the reader's language. The row therefore
 * carried two vocabularies for one kind at once -- "Tool call" next to 「工具调用」,
 * and the worse pair "Final answer" next to 「最终」 -- and the copy census could not
 * see either of them, because the strings sat in a `.ts` module the census does not
 * read. The word now comes from the same table the badge reads.
 */
describe("the step's own word", () => {
  it("is the word the row's badge shows, in both languages", () => {
    for (const kind of TRACE_KINDS) {
      expect(stepLabel(zh, kind, null), `zh ${kind}`).toBe(traceKindWord(zh, kind));
      expect(stepLabel(en, kind, null), `en ${kind}`).toBe(traceKindWord(en, kind));
    }
  });

  it("is the reader's sentence around the tool's name", () => {
    expect(stepLabel(en, "tool_result", { tool: "search_resume" })).toBe("search_resume result");
    expect(stepLabel(zh, "tool_result", { tool: "search_resume" })).toBe("search_resume 的结果");
    // A result row with no tool named says what it is; it does not read "undefined result".
    expect(stepLabel(zh, "tool_result", { ok: true })).toBe("工具结果");
    expect(stepLabel(en, "tool_result", { ok: true })).toBe("Tool result");
  });

  it("lands every kind the pipeline can publish, not a list the mapper keeps", () => {
    // The mapper used to carry its own copy of the roster, so a kind added to the
    // wire's list folded into `step_start` here first.
    for (const kind of TRACE_KINDS) {
      const { steps } = normalizeRunTrace(en, {
        run: { id: "r" },
        traces: [{ seq: 1, kind, payload: {} }],
      });
      expect(steps[0].kind, `${kind} was folded into step_start`).toBe(kind);
    }
  });
});
