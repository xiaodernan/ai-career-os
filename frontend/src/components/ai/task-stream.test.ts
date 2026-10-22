import { describe, expect, it } from "vitest";

import { asTraceKind, TRACE_KINDS } from "@/components/ai/task-stream";

describe("TRACE_KINDS", () => {
  it("lists every step kind the pipeline can publish", () => {
    expect(TRACE_KINDS).toEqual([
      "step_start",
      "tool_call",
      "tool_result",
      "llm_call",
      "retrieval",
      "rerank",
      "handoff",
      "message",
      "final",
    ]);
  });
});

describe("asTraceKind", () => {
  it("passes known trace kinds through unchanged", () => {
    for (const kind of TRACE_KINDS) {
      expect(asTraceKind(kind)).toBe(kind);
    }
  });

  it("maps anything else to step_start", () => {
    expect(asTraceKind("bogus")).toBe("step_start");
    expect(asTraceKind(123)).toBe("step_start");
    expect(asTraceKind(undefined)).toBe("step_start");
    expect(asTraceKind(null)).toBe("step_start");
  });
});
