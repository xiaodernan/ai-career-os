"use client";

import * as React from "react";
import Link from "next/link";
import { Waypoints } from "lucide-react";
import { ModuleView } from "@/components/common/module-view";
import { Pagination } from "@/components/common/pagination";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useActivityRuns } from "@/lib/hooks/resources";
import { useUrlState } from "@/lib/hooks/use-url-state";
import { runTotalTokens } from "@/lib/api/normalize";
import { formatDateTime, formatDuration, formatNumber, formatUsd, titleCase } from "@/lib/format";
import type { ActivityRun } from "@/lib/api/types";

// The route's own default window: `GET /activity/runs` binds `size` with
// `defaultValue = "30"`, so this number asks for exactly what the server would have
// chosen anyway -- the hook's own 30 literal never reaches the wire on this path.
const PAGE_SIZE = 30;

// Module-level so `setUrl` (a `useCallback` keyed on this object) is stable across renders.
const PAGE_DEFAULTS: { page: number } = { page: 0 };

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
  // The page index lives in the URL, so a reload or a shared list link opens the same window.
  const [state, setUrl] = useUrlState<{ page: number }>(
    PAGE_DEFAULTS,
    { numericKeys: ["page"] }
  );
  const runs = useActivityRuns({ page: state.page, size: PAGE_SIZE });

  const total = runs.data?.total ?? 0;
  // A past-the-end page is an empty window over a real total, not an empty list: the answer's
  // own window is the divisor (`data.size`, floored at 1 because a normalizer payload can
  // report 0), so the URL is corrected to the last page that exists. A layout effect, because
  // the stale commit paints its empty copy first -- React flushes this update before the
  // browser paints, so the wrong screen is replaced, not seen.
  const lastPage = runs.data
    ? Math.max(0, Math.ceil(total / Math.max(1, runs.data.size)) - 1)
    : 0;
  React.useLayoutEffect(() => {
    if (runs.data && state.page > lastPage) setUrl({ page: lastPage });
  }, [runs.data, state.page, lastPage, setUrl]);

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
      footer={
        total > PAGE_SIZE && (
          <Pagination
            page={runs.data?.page ?? state.page}
            size={PAGE_SIZE}
            total={total}
            label="runs"
            onPageChange={(page) => {
              setUrl({ page });
              window.scrollTo({ top: 0, behavior: "smooth" });
            }}
          />
        )
      }
      renderItem={(run) => <RunRow key={run.id} run={run} />}
    />
  );
}
