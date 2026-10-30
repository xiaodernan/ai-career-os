/**
 * The kinds an agent trace row carries.
 *
 * The values are the wire's: the pipelines publish `kind` (or `type`) on every trace
 * frame, and `asTraceKind` is the transport's gate — a stranger maps to `step_start`,
 * which is the row the timeline already falls back to for an unknown kind
 * (`KIND_META[event.kind] ?? KIND_META.step_start`). The type is derived from the
 * roster so a kind added here is a kind the timeline compiles against.
 */
export const TRACE_KINDS = [
  "step_start",
  "tool_call",
  "tool_result",
  "llm_call",
  "retrieval",
  "rerank",
  "handoff",
  "message",
  "final",
] as const;

export type TraceKind = (typeof TRACE_KINDS)[number];

export function asTraceKind(v: unknown): TraceKind {
  return (TRACE_KINDS as readonly string[]).includes(String(v)) ? (v as TraceKind) : "step_start";
}
