"use client";

import { Plus } from "lucide-react";
import { ModuleView } from "@/components/common/module-view";
import { Button } from "@/components/ui/button";
import { useApplications } from "@/lib/hooks/resources";
import { useCreateApplication, useReorderApplication } from "@/lib/hooks/actions";
import type { ApplicationStatus } from "@/lib/api/types";
import { KanbanBoard } from "@/components/common/kanban";

export default function ApplicationsPage() {
  const applications = useApplications({ size: 100 });
  const createApp = useCreateApplication();
  const reorderApp = useReorderApplication();

  const handleReorder = (id: string, status: ApplicationStatus, order: number) => {
    reorderApp.mutate({ id, status, order });
  };

  const handleCreate = () => {
    const title = prompt("Enter application title:");
    if (title?.trim()) {
      createApp.mutate({ title: title.trim() });
    }
  };

  return (
    <ModuleView
      title="Applications"
      description="Every role in flight. Drag cards across columns to move them — the dashboard counts follow the same data."
      query={applications}
      emptyHint={{
        title: "Pipeline is empty",
        description: "Track a job from its detail page and it appears here, starting in Saved.",
        action: (
          <Button variant="ai" size="sm" onClick={handleCreate} disabled={createApp.isPending}>
            Add application
          </Button>
        ),
      }}
      actions={
        <Button variant="outline" size="sm" onClick={handleCreate} disabled={createApp.isPending}>
          <Plus className="size-4 mr-2" aria-hidden />
          Add
        </Button>
      }
    >
      <KanbanBoard
        applications={applications.data?.items ?? []}
        onReorder={handleReorder}
        isPending={reorderApp.isPending}
      />
    </ModuleView>
  );
}
