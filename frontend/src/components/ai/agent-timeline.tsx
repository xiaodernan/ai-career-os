"use client";

import * as React from "react";
import { useLocale } from "@/lib/i18n/locale-context";
import {
  ArrowRightLeft,
  ChevronRight,
  Cpu,
  Flag,
  Footprints,
  MessageSquareText,
  Search,
  SlidersHorizontal,
  Wrench,
  CircleDashed,
  CheckCircle2,
  XCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * AgentTimeline — inspectable agent traces (architecture.md §4.5 agent_traces / §6.4).
 * tool_call · retrieval · rerank · llm_call · handoff · message · final …
 * Collapsible rows with icon, duration and JSON payload peek.
 */
export type TraceKind =
  | "step_start"
  | "tool_call"
  | "tool_result"
  | "llm_call"
  | "retrieval"
  | "rerank"
  | "handoff"
  | "message"
  | "final";

export type TraceStatus = "running" | "ok" | "error";

export interface AgentTraceEvent {
  id: string;
  kind: TraceKind;
  label: string;
  durationMs?: number;
  status?: TraceStatus;
  payload?: Record<string, unknown>;
}

const KIND_META: Record<TraceKind, { icon: React.ComponentType<{ className?: string }>; text: string }> = {
  step_start: { icon: Footprints, text: "text-muted-foreground" },
  tool_call: { icon: Wrench, text: "text-primary" },
  tool_result: { icon: Wrench, text: "text-muted-foreground" },
  llm_call: { icon: Cpu, text: "text-warning" },
  retrieval: { icon: Search, text: "text-success" },
  rerank: { icon: SlidersHorizontal, text: "text-success" },
  handoff: { icon: ArrowRightLeft, text: "text-primary" },
  message: { icon: MessageSquareText, text: "text-muted-foreground" },
  final: { icon: Flag, text: "text-foreground" },
};

export function formatDuration(ms?: number | null): string | null {
  if (ms == null) return null;
  return ms < 1000 ? `${Math.round(ms)}ms` : `${(ms / 1000).toFixed(1)}s`;
}

export interface AgentTimelineProps extends React.ComponentProps<"ul"> {
  events: AgentTraceEvent[];
  /** Start with rows containing payloads expanded */
  defaultExpanded?: boolean;
}

function AgentTimeline({ events, className, defaultExpanded = false, ...props }: AgentTimelineProps) {
  const { t } = useLocale();
  return (
    <ul
      aria-label="t("ai.agentTimeline.trace")"
      className={cn("flex flex-col text-sm", className)}
      {...props}
    >
      {events.map((evt, i) => (
        <TimelineRow key={evt.id} event={evt} isLast={i === events.length - 1} defaultExpanded={defaultExpanded} />
      ))}
    </ul>
  );
}

function TimelineRow({
  event,
  isLast,
  defaultExpanded,
}: {
  event: AgentTraceEvent;
  isLast: boolean;
  defaultExpanded: boolean;
}) {
  const [open, setOpen] = React.useState(defaultExpanded && event.payload != null);
  const meta = KIND_META[event.kind] ?? KIND_META.step_start;
  const Icon = meta.icon;
  const duration = formatDuration(event.durationMs);
  const hasPayload = event.payload != null;

  return (
    <li className="relative flex gap-3">
      <span className="flex flex-col items-center" aria-hidden>
        <span className={cn("flex h-7 items-center", meta.text)}>
          <Icon className="size-3.5" />
        </span>
        {!isLast && <span className="w-px flex-1 bg-border" />}
      </span>

      <div className="min-w-0 flex-1">
        <button
          type="button"
          disabled={!hasPayload}
          aria-expanded={hasPayload ? open : undefined}
          onClick={() => hasPayload && setOpen((o) => !o)}
          className={cn(
            "group flex h-7 w-full items-center gap-2 rounded-md text-left",
            hasPayload ? "cursor-pointer hover:bg-accent/60" : "cursor-default"
          )}
        >
          {hasPayload && (
            <ChevronRight
              className={cn("size-3 shrink-0 text-muted-foreground transition-transform duration-150", open && "rotate-90")}
              aria-hidden
            />
          )}
          <span className="truncate font-medium">{event.label}</span>
          <span className="shrink-0 text-2xs font-medium tracking-wide text-muted-foreground uppercase">
            {event.kind.replace("_", " ")}
          </span>
          <span className="ml-auto flex shrink-0 items-center gap-1.5 pr-1">
            {event.status === "running" && <CircleDashed className="size-3.5 animate-spin text-muted-foreground" aria-label="Running" />}
            {event.status === "ok" && <CheckCircle2 className="size-3.5 text-success" aria-label="Completed" />}
            {event.status === "error" && <XCircle className="size-3.5 text-destructive" aria-label="Failed" />}
            {duration && <span className="font-mono text-2xs text-muted-foreground tabular-nums">{duration}</span>}
          </span>
        </button>

        {open && hasPayload && (
          <pre className="animate-fade-in mb-2 max-h-56 overflow-auto rounded-lg border border-border/70 bg-muted/50 p-2.5 font-mono text-xs leading-relaxed text-muted-foreground">
            {JSON.stringify(event.payload, null, 2)}
          </pre>
        )}
      </div>
    </li>
  );
}

export { AgentTimeline };
