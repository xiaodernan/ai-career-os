"use client";

import * as React from "react";
import { endpoints } from "@/lib/api/endpoints";
import { useSSE, errorText, type SSEState } from "@/lib/sse/use-sse";
import { useLocale } from "@/lib/i18n/locale-context";
import {
  applyStatusEvent,
  type ProcessingStep,
  type StepStatus,
} from "@/components/ai/processing-steps";
import { ProcessingSteps } from "@/components/ai/processing-steps";
import { AgentTimeline, type AgentTraceEvent, type TraceKind } from "@/components/ai/agent-timeline";
import { cn } from "@/lib/utils";
import { ChevronRight } from "lucide-react";

/**
 * Task stream — the live progress surface for every async AI run.
 * `useTaskStream` subscribes to the SSE relay and folds it into ProcessingSteps +
 * an AgentTimeline. Of the names the transport declares, the pipelines publish
 * `status`, `progress`, `done`, `error` and a `ping` keep-alive; `token`, `trace`
 * and `artifact` have no producer yet (ai.stream() would emit the first, and
 * nothing calls it), so `text` stays empty and the trace drawer stays hidden until
 * one lands. It never invents progress: until the backend pushes something, the UI
 * says so.
 */

export const TRACE_KINDS: TraceKind[] = [
  "step_start",
  "tool_call",
  "tool_result",
  "llm_call",
  "retrieval",
  "rerank",
  "handoff",
  "message",
  "final",
];

export function asTraceKind(v: unknown): TraceKind {
  return (TRACE_KINDS as string[]).includes(String(v)) ? (v as TraceKind) : "step_start";
}

export interface UseTaskStreamOptions {
  /** Step ids + labels shown before the first SSE frame arrives. */
  seed?: { id: string; label: string }[];
  onDone?: (data: unknown) => void;
  onError?: (message: string) => void;
  /** Set false while the request hasn't started yet. */
  enabled?: boolean;
}

export interface TaskStreamState {
  steps: ProcessingStep[];
  traces: AgentTraceEvent[];
  /** Concatenated token stream (copilot answers, streaming text). */
  text: string;
  connection: SSEState;
  /** Anything received from the relay at all. */
  reporting: boolean;
  error: string | null;
  finished: boolean;
  running: boolean;
  stop: () => void;
}

export function useTaskStream(taskId: string | null | undefined, options: UseTaskStreamOptions = {}): TaskStreamState {
  const { seed = [], onDone, onError, enabled = true } = options;
  const { t } = useLocale();
  const [steps, setSteps] = React.useState<ProcessingStep[]>(() =>
    seed.map((s, i) => ({ ...s, status: (i === 0 ? "active" : "pending") as StepStatus }))
  );
  const [traces, setTraces] = React.useState<AgentTraceEvent[]>([]);
  const [text, setText] = React.useState("");
  const [reporting, setReporting] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [finished, setFinished] = React.useState(false);

  // Reset whenever a new task id comes in.
  const lastTask = React.useRef<string | null | undefined>(taskId);
  if (lastTask.current !== taskId) {
    lastTask.current = taskId;
    setSteps(seed.map((s, i) => ({ ...s, status: (i === 0 ? "active" : "pending") as StepStatus })));
    setTraces([]);
    setText("");
    setReporting(false);
    setError(null);
    setFinished(false);
  }

  const url = enabled && taskId ? endpoints.aiStream(taskId) : null;

  const { state, stop } = useSSE({
    url,
    onStatus: (data) => {
      setReporting(true);
      setSteps((prev) => applyStatusEvent(prev, data));
    },
    onTrace: (data) => {
      setReporting(true);
      const id = String(data.id ?? `t-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`);
      const next: AgentTraceEvent = {
        id,
        kind: asTraceKind(data.kind ?? data.type),
        label: String(data.label ?? data.name ?? data.kind ?? "step"),
        durationMs: typeof data.durationMs === "number" ? data.durationMs : undefined,
        status: data.status === "error" ? "error" : data.status === "ok" || data.status === "done" ? "ok" : "running",
        payload: data.payload && typeof data.payload === "object" ? (data.payload as Record<string, unknown>) : undefined,
      };
      setTraces((prev) => {
        const idx = prev.findIndex((t) => t.id === id);
        if (idx >= 0) {
          const merged = [...prev];
          merged[idx] = { ...merged[idx], ...next, status: next.status ?? "ok" };
          return merged;
        }
        // a new step means the previous running one is done
        const settled = prev.map((t) => (t.status === "running" ? { ...t, status: "ok" as const } : t));
        return [...settled, next];
      });
    },
    onToken: (token) => {
      setReporting(true);
      setText((prev) => prev + token);
    },
    onArtifact: () => setReporting(true),
    onDone: (data) => {
      setReporting(true);
      setFinished(true);
      setSteps((prev) =>
        prev.map((s) => (s.status === "active" || s.status === "pending" ? { ...s, status: "done" } : s))
      );
      setTraces((prev) => prev.map((t) => (t.status === "running" ? { ...t, status: "ok" } : t)));
      onDone?.(data);
    },
    onError: (data) => {
      const message = errorText(data) ?? t("ai.taskStream.runError");
      setError(message);
      setFinished(true);
      setSteps((prev) => prev.map((s) => (s.status === "active" ? { ...s, status: "error" } : s)));
      onError?.(message);
    },
    onTransportError: () => {
      // The run itself may still succeed over the JSON response — don't fake it.
      setReporting(false);
    },
  });

  return {
    steps,
    traces,
    text,
    connection: state,
    reporting,
    error,
    finished,
    running: Boolean(url) && !finished && !error,
    stop,
  };
}

/* ------------------------------------------------------------------ */

export interface TaskProgressProps extends React.ComponentProps<"div"> {
  taskId?: string | null;
  /** Local stage hints (mutating request in flight without a task id yet). */
  steps?: ProcessingStep[];
  traces?: AgentTraceEvent[];
  /** Fallback: request is pending but no task id has been returned yet. */
  pending?: boolean;
  pendingLabel?: string;
  /** Translation key for pendingLabel (overrides pendingLabel if provided). */
  pendingLabelKey?: string;
  /** Step labels to show before the first SSE status frame arrives. */
  seed?: { id: string; label: string }[];
  title?: string;
  showTimeline?: boolean;
  onDone?: (data: unknown) => void;
}

function TaskProgress({
  taskId,
  steps: externalSteps,
  traces: externalTraces,
  pending = false,
  pendingLabel,
  pendingLabelKey = "ai.taskStream.waitingForAgent",
  seed,
  title,
  showTimeline = true,
  onDone,
  className,
  ...props
}: TaskProgressProps) {
  const stream = useTaskStream(taskId, { seed, onDone });
  const { t } = useLocale();
  const steps = externalSteps ?? stream.steps;
  const traces = externalTraces ?? stream.traces;
  const live = Boolean(taskId) || pending;
  const [timelineOpen, setTimelineOpen] = React.useState(false);
  const effectivePendingLabel = pendingLabel ?? t(pendingLabelKey);

  if (!live) return null;

  return (
    <div className={cn("space-y-3", className)} {...props}>
      {title && (
        <p className="text-2xs font-medium tracking-wide text-muted-foreground uppercase">{title}</p>
      )}
      {steps.length > 0 ? (
        <ProcessingSteps steps={pending && !stream.reporting ? [{ id: "wait", label: effectivePendingLabel, status: "active" }, ...steps] : steps} />
      ) : (
        <ProcessingSteps steps={[{ id: "wait", label: effectivePendingLabel, status: "active" }]} />
      )}

      {Boolean(taskId) && !stream.reporting && !stream.finished && (
        <p className="text-xs text-muted-foreground">
          {t("ai.taskStream.streamNotReported")}
        </p>
      )}

      {stream.error && <p className="text-xs text-destructive">{stream.error}</p>}

      {showTimeline && traces.length > 0 && (
        <div className="rounded-lg border border-border/70 bg-muted/30">
          <button
            type="button"
            onClick={() => setTimelineOpen((o) => !o)}
            aria-expanded={timelineOpen}
            className="flex w-full items-center gap-1.5 px-3 py-2 text-left text-xs font-medium text-muted-foreground hover:text-foreground focus-visible:ring-[3px] focus-visible:ring-primary/30 rounded-md"
          >
            <ChevronRight className={cn("size-3 transition-transform duration-150", timelineOpen && "rotate-90")} aria-hidden />
            {t("ai.taskStream.agentTrace")}
            <span className="ml-auto tabular-nums">{t("ai.taskStream.steps", { count: traces.length })}</span>
          </button>
          {timelineOpen && (
            <div className="px-3 pb-3">
              <AgentTimeline events={traces} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export { TaskProgress };

/** Small helper for local (non-SSE) stage hints driven by a mutation's own state. */
export function localStages(labels: string[], index: number): ProcessingStep[] {
  return labels.map((label, i) => ({
    id: `stage-${i}`,
    label,
    status: (i < index ? "done" : i === index ? "active" : "pending") as StepStatus,
  }));
}

