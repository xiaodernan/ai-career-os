"use client";

import { CalendarClock } from "lucide-react";
import { ModuleView } from "@/components/common/module-view";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useApplications } from "@/lib/hooks/resources";

const STAGE_VARIANT: Record<string, "success" | "warning" | "destructive" | "secondary" | "ai"> = {
  saved: "secondary",
  applied: "ai",
  oa: "ai",
  interview: "warning",
  final_round: "warning",
  offer: "success",
  rejected: "destructive",
};

export default function ApplicationsPage() {
  const applications = useApplications({ size: 50 });
  return (
    <ModuleView
      title="Applications"
      description="Every role in flight — the kanban board ships with drag-and-drop status changes; this list mirrors the same data."
      query={applications}
      emptyHint={{
        title: "Pipeline is empty",
        description: "Match a job and track it from saved to offer. Reminders included.",
      }}
      renderItem={(app) => (
        <Card key={app.id}>
          <CardContent className="flex items-center gap-3">
            <span className="flex size-9 items-center justify-center rounded-lg bg-muted text-muted-foreground">
              <CalendarClock className="size-4.5" aria-hidden />
            </span>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium">{app.title}</p>
              <p className="truncate text-xs text-muted-foreground">
                {app.company?.name}
                {app.reminderAt && <> · reminder {new Date(app.reminderAt).toLocaleDateString()}</>}
              </p>
            </div>
            <Badge variant={STAGE_VARIANT[app.status] ?? "secondary"} className="capitalize">
              {app.status.replace("_", " ")}
            </Badge>
          </CardContent>
        </Card>
      )}
    />
  );
}
