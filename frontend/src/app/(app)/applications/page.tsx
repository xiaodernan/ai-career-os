"use client";

import { CalendarClock } from "lucide-react";
import { ModuleView } from "@/components/common/module-view";
import { Card, CardContent } from "@/components/ui/card";
import { badgeVariants } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { useApplications } from "@/lib/hooks/resources";
import { useUpdateApplication } from "@/lib/hooks/actions";
import type { Application, ApplicationStatus } from "@/lib/api/types";
import { pickerStages, stageMeta } from "@/lib/pipeline";

/**
 * The row's stage pill *is* the control: PATCH /applications/{id} has been live
 * since the first backend commit, and the only thing that ever moved a role out
 * of `saved` was creating it from the job page.
 */
function StagePicker({ app }: { app: Application }) {
  const update = useUpdateApplication();
  return (
    <select
      aria-label={`Stage for ${app.title}`}
      value={app.status}
      disabled={update.isPending}
      onChange={(e) =>
        update.mutate({ id: app.id, patch: { status: e.target.value as ApplicationStatus } })
      }
      className={cn(
        badgeVariants({ variant: stageMeta(app.status).badgeVariant }),
        "capitalize focus-visible:ring-[3px] focus-visible:ring-primary/30"
      )}
    >
      {pickerStages(app.status).map((s) => (
        <option key={s.value} value={s.value}>
          {s.label}
        </option>
      ))}
    </select>
  );
}

export default function ApplicationsPage() {
  const applications = useApplications({ size: 50 });
  return (
    <ModuleView
      title="Applications"
      description="Every role in flight. Pick a stage on any row to move it — the dashboard counts follow the same data."
      query={applications}
      emptyHint={{
        title: "Pipeline is empty",
        description: "Track a job from its detail page and it appears here, starting in Saved.",
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
            <StagePicker app={app} />
          </CardContent>
        </Card>
      )}
    />
  );
}
