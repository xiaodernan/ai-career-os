import type { AgentTraceEvent, TraceStatus } from "@/components/ai/agent-timeline";
import { asTraceKind, type TraceKind } from "@/lib/trace-kinds";
import { traceKindWord } from "@/lib/status-words";

/**
 * The reader's translator — `useLocale().t`.
 *
 * One line this mapper builds is a sentence with the step's own value inside it, so the
 * word functions' `TranslateFn` (a key only) is too narrow here; the wider function is
 * still a `TranslateFn` wherever it is handed on.
 */
type Translate = (key: string, vars?: Record<string, string | number>) => string;

/**
 * Trace mapping for GET /activity/runs/{id}, which answers
 * `{ run, traces: [{ seq, kind, agent, payload, createdAt }] }`.
 * The payload shape differs per step kind (written by the agent orchestrator),
 * so every label here is read from the persisted payload — never invented. When a
 * step carries no text of its own the label is the kind's word from the reader's
 * table, which is the same word the row's badge shows beside it.
 */

export interface RunSummary {
  id: string;
  agent?: string;
  trigger?: string;
  status?: string;
  model?: string;
  inputTokens?: number;
  outputTokens?: number;
  cachedTokens?: number;
  costUsd?: number;
  latencyMs?: number;
  error?: string;
  startedAt?: string;
  finishedAt?: string;
  rootRunId?: string;
  conversationId?: string;
}

export interface RunTrace {
  run: RunSummary;
  steps: AgentTraceEvent[];
}

function rec(value: unknown): Record<string, unknown> | null {
  return value != null && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

function str(obj: Record<string, unknown> | null | undefined, ...keys: string[]): string | undefined {
  for (const k of keys) {
    const v = obj?.[k];
    if (typeof v === "string" && v.trim()) return v;
    if (typeof v === "number") return String(v);
  }
  return undefined;
}

function num(obj: Record<string, unknown> | null | undefined, ...keys: string[]): number | undefined {
  for (const k of keys) {
    const v = obj?.[k];
    if (typeof v === "number" && Number.isFinite(v)) return v;
  }
  return undefined;
}

function bool(value: unknown): boolean | undefined {
  return typeof value === "boolean" ? value : undefined;
}

export function normalizeRun(raw: unknown): RunSummary {
  const body = rec(raw) ?? {};
  const run = rec(body.run) ?? body;
  return {
    id: str(run, "id", "runId", "run_id") ?? "",
    agent: str(run, "agent", "agentName", "agent_name"),
    trigger: str(run, "trigger", "kind", "task"),
    status: str(run, "status", "state"),
    model: str(run, "model", "modelName"),
    inputTokens: num(run, "inputTokens", "input_tokens", "tokensIn", "promptTokens"),
    outputTokens: num(run, "outputTokens", "output_tokens", "tokensOut", "completionTokens"),
    cachedTokens: num(run, "cachedTokens", "cached_tokens"),
    costUsd: num(run, "costUsd", "cost_usd"),
    latencyMs: num(run, "latencyMs", "latency_ms", "durationMs"),
    error: str(run, "error", "errorMessage"),
    startedAt: str(run, "startedAt", "started_at"),
    finishedAt: str(run, "finishedAt", "finished_at"),
    rootRunId: str(run, "rootRunId", "root_run_id"),
    conversationId: str(run, "conversationId", "conversation_id"),
  };
}

/**
 * A short, honest one-line label for a persisted trace step.
 *
 * The step's own text comes first — the tool name, the model, the query the agent ran.
 * When the payload carries none, the label is the kind's word from the reader's table,
 * the same word the timeline's badge shows on that row; the mapper used to return its
 * own English phrase there, so a Chinese row read "Tool call" beside 「工具调用」.
 */
export function stepLabel(
  t: Translate,
  kind: TraceKind,
  payload: Record<string, unknown> | null
): string {
  const word = traceKindWord(t, kind);
  switch (kind) {
    case "step_start":
      return str(payload, "stage", "name") ?? word;
    case "llm_call": {
      const model = str(payload, "model");
      const step = str(payload, "kind", "step");
      return [step, model].filter(Boolean).join(" · ") || word;
    }
    case "tool_call":
      return str(payload, "tool", "name") ?? word;
    case "tool_result": {
      // "web_search result" is a sentence around a value, so the reader's table holds
      // the whole line; with no tool named, the step's word says the same thing.
      const tool = str(payload, "tool", "name");
      return tool ? t("ai.agentTimeline.resultOf", { tool }) : word;
    }
    case "retrieval":
      return str(payload, "query", "text") ?? word;
    case "rerank":
      return str(payload, "strategy", "model") ?? word;
    case "handoff":
      return str(payload, "to", "agent", "target") ?? word;
    case "message":
      return str(payload, "role", "text", "message") ?? word;
    case "final":
      return str(payload, "answer_preview", "answer") ?? word;
  }
}

/** tool_result carries ok:false; a failed run marks its last step as such. */
export function stepStatus(kind: TraceKind, payload: Record<string, unknown> | null, runFailed: boolean, isLast: boolean): TraceStatus | undefined {
  if (kind === "tool_result") {
    const ok = bool(payload?.ok);
    if (ok === false) return "error";
    if (ok === true) return "ok";
    return undefined;
  }
  if (isLast && runFailed) return "error";
  return undefined;
}

export function normalizeRunTrace(t: Translate, raw: unknown): RunTrace {
  const body = rec(raw) ?? {};
  const run = normalizeRun(body);
  const rawTraces = Array.isArray(body.traces)
    ? body.traces
    : Array.isArray(body.steps)
      ? body.steps
      : [];
  const runFailed = run.status === "failed" || run.status === "error";

  const steps = rawTraces.map((entry, index): AgentTraceEvent => {
    const item = rec(entry) ?? {};
    const payload = rec(item.payload) ?? rec(item.data) ?? (Object.keys(item).length > 2 ? item : null);
    const rawKind = str(item, "kind", "type", "event") ?? "step_start";
    const kind = asTraceKind(rawKind);
    const seq = num(item, "seq", "sequence", "index");
    return {
      id: str(item, "id") ?? `step-${seq ?? index}`,
      kind,
      label: stepLabel(t, kind, payload),
      durationMs: num(payload, "latency_ms", "latencyMs", "duration_ms"),
      status: stepStatus(kind, payload, runFailed, index === rawTraces.length - 1),
      payload: payload ?? undefined,
    };
  });

  return { run, steps };
}

/** Totals roll up from the run row, falling back to summing the persisted steps. */
export function traceTotals(trace: RunTrace): {
  tokens: number | undefined;
  costUsd: number | undefined;
  toolCalls: number;
  llmCalls: number;
  failedSteps: number;
} {
  const { run, steps } = trace;
  let toolCalls = 0;
  let llmCalls = 0;
  let stepTokens = 0;
  let stepCost = 0;
  for (const s of steps) {
    if (s.kind === "tool_call") toolCalls += 1;
    if (s.kind === "llm_call") llmCalls += 1;
    stepTokens += (num(s.payload, "in_tokens") ?? 0) + (num(s.payload, "out_tokens") ?? 0);
    stepCost += num(s.payload, "cost_usd") ?? 0;
  }
  return {
    tokens: (run.inputTokens ?? 0) + (run.outputTokens ?? 0) || stepTokens || undefined,
    costUsd: run.costUsd || stepCost || undefined,
    toolCalls,
    llmCalls,
    failedSteps: steps.filter((s) => s.status === "error").length,
  };
}
