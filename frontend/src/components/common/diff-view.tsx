"use client";

import * as React from "react";
import { ArrowRight, Check, Minus, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { AIBadge } from "@/components/ai/ai-badge";
import { useLocale } from "@/lib/i18n/locale-context";
import type { TailorChange } from "@/lib/api/types";

/**
 * DiffView — AI resume tailoring shown as accepted vs rejected changes.
 * Rejected rows stay visible with their reason: transparency over noise, and
 * nothing is presented as applied that the agent refused to apply (§11:
 * no invented experience).
 */

export interface DiffViewProps extends React.ComponentProps<"div"> {
  accepted: TailorChange[];
  rejected?: TailorChange[];
  /** Shows the tailoring notes the model asked the candidate to double-check */
  notes?: string[];
  stats?: Record<string, unknown>;
}

function ChangeRow({ change, kind }: { change: TailorChange; kind: "accepted" | "rejected" }) {
  const { t } = useLocale();
  const accepted = kind === "accepted";
  return (
    <li
      className={cn(
        "rounded-lg border p-3",
        accepted ? "border-success/25 bg-success/5" : "border-border/70 bg-muted/40"
      )}
    >
      <div className="flex items-center gap-2">
        <span
          className={cn(
            "flex size-4.5 items-center justify-center rounded-full",
            accepted ? "bg-success/15 text-success" : "bg-muted text-muted-foreground"
          )}
          aria-hidden
        >
          {accepted ? <Check className="size-3" strokeWidth={3} /> : <Minus className="size-3" strokeWidth={3} />}
        </span>
        <p className="min-w-0 flex-1 truncate text-xs font-semibold">
          {change.section ?? t("diffView.bullet")}
        </p>
        <AIBadge label={accepted ? t("diffView.applied") : t("diffView.skipped")} className={accepted ? undefined : "border-border bg-muted text-muted-foreground"} />
      </div>

      <div className="mt-2 space-y-1.5 text-sm">
        {change.before && (
          <p className="flex gap-2 text-muted-foreground">
            <span className="mt-0.5 shrink-0 font-mono text-2xs text-destructive" aria-hidden>-</span>
            <span className={cn("min-w-0", !accepted && "line-through decoration-border")}>{change.before}</span>
          </p>
        )}
        {change.after && (
          <p className="flex gap-2">
            <span className="mt-0.5 shrink-0 font-mono text-2xs text-success" aria-hidden>+</span>
            <span className="min-w-0">{change.after}</span>
          </p>
        )}
        {!change.before && change.after && (
          <p className="flex gap-2">
            <ArrowRight className="mt-0.5 size-3 shrink-0 text-muted-foreground" aria-hidden />
            <span>{change.after}</span>
          </p>
        )}
      </div>

      {change.reason && (
        <p className="mt-2 border-t border-border/60 pt-2 text-xs text-muted-foreground">
          <span className={cn("font-medium", accepted ? "text-foreground" : "text-warning")}>
            {accepted ? t("diffView.why") : t("diffView.whyNotApplied")}
          </span>
          {change.reason}
        </p>
      )}
    </li>
  );
}

function DiffView({ accepted, rejected = [], notes, stats, className, ...props }: DiffViewProps) {
  const { t } = useLocale();
  const [showRejected, setShowRejected] = React.useState(false);
  if (!accepted.length && !rejected.length) return null;
  const statChips = stats
    ? Object.entries(stats)
        .filter(([, v]) => typeof v === "number")
        .slice(0, 4)
    : [];

  return (
    <div className={cn("space-y-4", className)} {...props}>
      {(notes?.length ?? 0) > 0 && (
        <div className="rounded-lg border border-warning/25 bg-warning/10 p-3">
          <p className="flex items-center gap-1.5 text-xs font-semibold text-warning">
            <Sparkles className="size-3.5" aria-hidden />
            {t("diffView.agentNotes")}
          </p>
          <ul className="mt-1.5 ml-4 list-disc space-y-1 text-xs text-muted-foreground">
            {notes!.map((n, i) => (
              <li key={i}>{n}</li>
            ))}
          </ul>
        </div>
      )}

      {statChips.length > 0 && (
        <ul className="flex flex-wrap gap-1.5" aria-label={t("diffView.statistics")}>
          {statChips.map(([k, v]) => (
            <li key={k}>
              <Badge variant="outline" className="text-2xs tabular-nums">
                {k.replace(/_/g, " ")}: <span className="font-medium text-foreground">{String(v)}</span>
              </Badge>
            </li>
          ))}
        </ul>
      )}

      <section className="space-y-2">
        <h4 className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
          {t("diffView.appliedChanges")}{" "}
          <span className="text-foreground tabular-nums">{accepted.length}</span>
        </h4>
        {accepted.length ? (
          <ul className="space-y-2">
            {accepted.map((c) => (
              <ChangeRow key={c.id} change={c} kind="accepted" />
            ))}
          </ul>
        ) : (
          <p className="text-sm text-muted-foreground">
            {t("diffView.noSafeEdits")}
          </p>
        )}
      </section>

      {rejected.length > 0 && (
        <section className="space-y-2">
          <button
            type="button"
            onClick={() => setShowRejected((v) => !v)}
            aria-expanded={showRejected}
            className="flex w-full items-center gap-2 rounded-lg border border-border/70 bg-muted/40 px-3 py-2 text-left text-xs font-semibold text-muted-foreground hover:bg-accent focus-visible:ring-[3px] focus-visible:ring-primary/30"
          >
            <Minus className="size-3.5" aria-hidden />
            {t("diffView.rejectedProposals")}
            <span className="tabular-nums">{rejected.length}</span>
            <span className="ml-auto text-2xs">
              {showRejected ? t("diffView.hide") : t("diffView.showReasons")}
            </span>
          </button>
          {showRejected && (
            <ul className="space-y-2">
              {rejected.map((c) => (
                <ChangeRow key={c.id} change={c} kind="rejected" />
              ))}
            </ul>
          )}
        </section>
      )}
    </div>
  );
}

export { DiffView };
