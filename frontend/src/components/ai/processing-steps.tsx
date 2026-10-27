"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { Check, Circle, TriangleAlert } from "lucide-react";
import { useLocale } from "@/lib/i18n/locale-context";

/**
 * ProcessingSteps — the vertical checklist driven by SSE `status` events.
 * pending ○ · active ● (pulsing, shimmer label) · done ✓ · error ⚠
 */
export type StepStatus = "pending" | "active" | "done" | "error";

export interface ProcessingStep {
  id: string;
  label: string;
  status: StepStatus;
  detail?: string;
}

export interface ProcessingStepsProps extends React.ComponentProps<"ol"> {
  steps: ProcessingStep[];
}

function ProcessingSteps({ steps, className, ...props }: ProcessingStepsProps) {
  const { t } = useLocale();
  return (
    <ol
      aria-label={t("ai.processing.ariaLabel")}
      className={cn("flex flex-col gap-0.5", className)}
      {...props}
    >
      {steps.map((step, i) => (
        <Step
          key={step.id}
          step={step}
          isLast={i === steps.length - 1}
        />
      ))}
    </ol>
  );
}

function Step({ step, isLast }: { step: ProcessingStep; isLast: boolean }) {
  const dot =
    step.status === "done" ? (
      <span className="flex size-4.5 items-center justify-center rounded-full bg-success/15 text-success">
        <Check className="size-3" strokeWidth={3} aria-hidden />
      </span>
    ) : step.status === "error" ? (
      <span className="flex size-4.5 items-center justify-center rounded-full bg-destructive/15 text-destructive">
        <TriangleAlert className="size-3" aria-hidden />
      </span>
    ) : step.status === "active" ? (
      <span className="relative flex size-4.5 items-center justify-center">
        <span
          aria-hidden
          className="absolute size-4.5 animate-pulse-dot rounded-full bg-primary/25"
        />
        <span className="size-2 rounded-full bg-primary" />
      </span>
    ) : (
      <Circle className="size-4.5 text-border" aria-hidden />
    );

  return (
    <li
      aria-current={step.status === "active" ? "step" : undefined}
      className="relative flex gap-3"
    >
      <span className="flex flex-col items-center">
        <span className="flex h-7 items-center">{dot}</span>
        {!isLast && (
          <span
            aria-hidden
            className={cn(
              "w-px flex-1",
              step.status === "done" ? "bg-success/30" : "bg-border"
            )}
          />
        )}
      </span>
      <span className="flex min-w-0 flex-1 flex-col pb-1.5 pt-1.5">
        <span
          className={cn(
            "text-sm leading-none",
            step.status === "pending" && "text-muted-foreground/70",
            step.status === "active" && "shimmer-text font-medium",
            step.status === "done" && "text-foreground",
            step.status === "error" && "text-destructive"
          )}
        >
          {step.label}
        </span>
        {step.detail && (
          <span className="mt-1 text-xs text-muted-foreground">{step.detail}</span>
        )}
      </span>
    </li>
  );
}

/**
 * A `status` or `progress` frame from the run stream.
 *
 * `state` is what the ai-service pipelines actually send (`{"step","state"}`,
 * `{"step","done","total"}`); `status`/`progress` are kept because callers that
 * pre-date the pipelines normalize into them.
 */
export interface StatusEvent {
  step?: string;
  label?: string;
  state?: string;
  status?: string;
  progress?: number;
  done?: number;
  total?: number;
  /** Frames ride along with more than the fold reads: `count`, `intent`, `agent`. */
  [key: string]: unknown;
}

export function statusFromEvent(evt: StatusEvent): StepStatus {
  const s = evt.state ?? evt.status;
  if (s === "done" || evt.progress === 100) return "done";
  if (s === "error") return "error";
  return "active";
}

/** "64 / 200" for a counted progress frame, undefined for a plain status flip. */
export function progressDetail(evt: StatusEvent): string | undefined {
  if (typeof evt.done !== "number" || typeof evt.total !== "number") return undefined;
  return `${evt.done} / ${evt.total}`;
}

/**
 * The one place a stage list becomes a seeded step list.
 *
 * The request lifecycle is observable (a request is in flight, or it answered);
 * the internal position of a batch operation is not, so a run shows its first
 * stage active and the rest pending, an answered run shows all done, and an
 * untouched list WAITS — `"pending"` on an idle row would claim work that has
 * not started, the same lie a fired-but-unsent progress bar tells.
 *
 * `prefix` namespaces the ids (React keys); the lifecycle seeds describe no wire
 * step, so unlike the ingest seed these ids never match a frame.
 */
export function seedSteps(
  stages: string[],
  state: "idle" | "pending" | "done",
  prefix: string,
): ProcessingStep[] {
  return stages.map((label, i) => ({
    id: `${prefix}-${i}`,
    label,
    status: state === "done" ? "done" : state === "pending" && i === 0 ? "active" : "pending",
  }));
}

/**
 * Small helper to fold SSE `status` events into a steps array.
 * Unknown incoming steps are appended automatically.
 */
export function applyStatusEvent(prev: ProcessingStep[], evt: StatusEvent): ProcessingStep[] {
  if (!evt.step) return prev;
  const idx = prev.findIndex((s) => s.id === evt.step);
  const status = statusFromEvent(evt);
  const updated: ProcessingStep[] = [...prev];
  const next: ProcessingStep = {
    id: evt.step,
    label: evt.label ?? updated[idx]?.label ?? evt.step,
    status,
    detail: progressDetail(evt) ?? updated[idx]?.detail,
  };
  if (idx === -1) {
    // Everything that was `active` before this step finished.
    const fixed = updated.map((s) => (s.status === "active" ? { ...s, status: "done" as StepStatus } : s));
    fixed.push(next);
    return fixed;
  }
  updated[idx] = next;
  if (status === "active") {
    for (let i = 0; i < idx; i++) {
      if (updated[i].status === "active" || updated[i].status === "pending") {
        updated[i] = { ...updated[i], status: "done" };
      }
    }
  }
  return updated;
}

export { ProcessingSteps };
