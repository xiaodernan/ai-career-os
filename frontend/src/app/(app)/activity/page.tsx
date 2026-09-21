"use client";

import { Waypoints } from "lucide-react";
import { ModuleView } from "@/components/common/module-view";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { AgentTimeline } from "@/components/ai/agent-timeline";
import { useActivity } from "@/lib/hooks/resources";

export default function ActivityPage() {
  const activity = useActivity();
  return (
    <ModuleView
      title="AI Activity"
      description="Every agent run, tool call and retrieval — the debug view behind the answers."
      query={activity}
      emptyHint={{
        title: "No agent runs yet",
        description: "Once Copilot or a matching job runs, its full trace appears here.",
      }}
      ctaHref="/copilot"
      ctaLabel="Run something in Copilot"
      renderItem={(evt) => (
        <Card key={evt.id}>
          <CardContent className="flex items-start gap-3">
            <span className="mt-0.5 flex size-9 items-center justify-center rounded-lg bg-muted text-muted-foreground">
              <Waypoints className="size-4.5" aria-hidden />
            </span>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium">{evt.summary ?? evt.kind}</p>
              <p className="text-xs text-muted-foreground">
                {new Date(evt.createdAt).toLocaleString()}
              </p>
              <div className="mt-2">
                <AgentTimeline
                  events={[
                    {
                      id: evt.id,
                      kind: "step_start",
                      label: `agent: ${evt.agent ?? "career"}`,
                      status: evt.status === "ok" || evt.status === "completed" ? "ok" : evt.status === "error" ? "error" : "running",
                    },
                  ]}
                />
              </div>
            </div>
            {evt.status && (
              <Badge variant={evt.status === "ok" || evt.status === "completed" ? "success" : evt.status === "error" ? "destructive" : "warning"} className="capitalize">
                {evt.status}
              </Badge>
            )}
          </CardContent>
        </Card>
      )}
    />
  );
}
