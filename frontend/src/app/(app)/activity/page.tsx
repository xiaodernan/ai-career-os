"use client";

import Link from "next/link";
import { Waypoints } from "lucide-react";
import { ModuleView } from "@/components/common/module-view";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { AgentTimeline } from "@/components/ai/agent-timeline";
import { useActivityRuns } from "@/lib/hooks/resources";
import type { ActivityRun } from "@/lib/api/types";

function statusVariant(status?: string) {
  if (status === "ok" || status === "completed" || status === "succeeded") return "success" as const;
  if (status === "error" || status === "failed") return "destructive" as const;
  return "warning" as const;
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
      renderItem={(evt) => {
        const when = evt.startedAt ?? evt.createdAt;
        const card = (
          <Card>
            <CardContent className="flex items-start gap-3">
              <span className="mt-0.5 flex size-9 items-center justify-center rounded-lg bg-muted text-muted-foreground">
                <Waypoints className="size-4.5" aria-hidden />
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium">{evt.summary ?? evt.kind ?? "Agent run"}</p>
                <p className="text-xs text-muted-foreground">
                  {when ? new Date(when).toLocaleString() : ""}
                  {evt.durationMs != null && ` · ${Math.round(evt.durationMs)}ms`}
                  {evt.model && ` · ${evt.model}`}
                  {(evt.tokensIn != null || evt.tokensOut != null) &&
                    ` · ${evt.tokensIn ?? 0}↓ ${evt.tokensOut ?? 0}↑ tok`}
                  {evt.costUsd != null && evt.costUsd > 0 && ` · $${evt.costUsd.toFixed(4)}`}
                </p>
                <div className="mt-2">
                  <AgentTimeline
                    events={[
                      {
                        id: evt.id,
                        kind: "step_start",
                        label: `agent: ${evt.agent ?? "career"}`,
                        status:
                          evt.status === "ok" || evt.status === "completed" || evt.status === "succeeded"
                            ? "ok"
                            : evt.status === "error" || evt.status === "failed"
                              ? "error"
                              : "running",
                      },
                    ]}
                  />
                </div>
              </div>
              {evt.status && (
                <Badge variant={statusVariant(evt.status)} className="capitalize">
                  {evt.status}
                </Badge>
              )}
            </CardContent>
          </Card>
        );
        return evt.relatedHref ? (
          <Link key={evt.id} href={evt.relatedHref} className="block">
            {card}
          </Link>
        ) : (
          <div key={evt.id}>{card}</div>
        );
      }}
    />
  );
}
