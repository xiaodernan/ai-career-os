"use client";

import Link from "next/link";
import { Waypoints } from "lucide-react";
import { ModuleView } from "@/components/common/module-view";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useActivityRuns } from "@/lib/hooks/resources";
import { runTotalTokens } from "@/lib/api/normalize";
import { formatDateTime, formatDuration, formatNumber, formatUsd, titleCase } from "@/lib/format";
import type { ActivityRun } from "@/lib/api/types";

/**
 * AI activity log. Field names follow the backend `RunItem` contract as mapped
 * by normalizeRun: agent · kind(=trigger) · status · durationMs(=latencyMs) ·
 * tokensIn/tokensOut(=input/outputTokens) · costUsd · startedAt/finishedAt.
 */

function statusVariant(status?: string) {
  if (status === "ok" || status === "completed" || status === "succeeded") return "success" as const;
  if (status === "error" || status === "failed") return "destructive" as const;
  return "warning" as const;
}

function RunRow({ run }: { run: ActivityRun }) {
  const when = run.startedAt;
  const tokens = runTotalTokens(run);

  return (
    <Card className="transition-colors hover:border-primary/40">
      <CardContent className="flex items-start gap-3">
        <span className="mt-0.5 flex size-9 shrink-0 items-center justify-center rounded-lg bg-muted text-muted-foreground">
          <Waypoints className="size-4" aria-hidden />
        </span>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium">
            {`${run.agent ?? "career"} · ${run.kind ?? "run"}`}
          </p>
          <p className="mt-0.5 text-xs text-muted-foreground">
            {when ? formatDateTime(when) : "—"}
            {run.durationMs ? ` · ${formatDuration(run.durationMs)}` : ""}
            {run.model && ` · ${run.model}`}
            {tokens ? ` · ${formatNumber(tokens)} tok` : ""}
            {run.costUsd ? ` · ${formatUsd(run.costUsd)}` : ""}
          </p>
          {run.error && (
            <p className="mt-1 truncate font-mono text-xs text-destructive">{run.error}</p>
          )}
        </div>
        <div className="flex shrink-0 flex-col items-end gap-2">
          {run.status && (
            <Badge variant={statusVariant(run.status)} className="capitalize">
              {titleCase(run.status)}
            </Badge>
          )}
          <Button variant="ghost" size="xs" asChild>
            <Link href={`/activity/${run.id}`}>Trace</Link>
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

export default function ActivityPage() {
  const runs = useActivityRuns();
  return (
    <ModuleView<ActivityRun>
      title="AI Activity"
      description="Every agent run, tool call and retrieval — the debug view behind the answers."
      query={runs}
      emptyHint={{
        title: "No agent runs yet",
        description: "Once Copilot or a matching job runs, its full trace appears here.",
      }}
      ctaHref="/copilot"
      ctaLabel="Run something in Copilot"
      renderItem={(run) => <RunRow key={run.id} run={run} />}
    />
  );
}
