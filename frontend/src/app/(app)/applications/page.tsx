"use client";

import * as React from "react";
import { Plus } from "lucide-react";
import { ModuleView } from "@/components/common/module-view";
import { Button } from "@/components/ui/button";
import { useApplications } from "@/lib/hooks/resources";
import { useReorderApplication } from "@/lib/hooks/actions";
import type { Application, ApplicationStatus } from "@/lib/api/types";
import { KanbanBoard } from "@/components/common/kanban";
import { ApplicationDialog } from "@/components/applications/application-dialog";

export default function ApplicationsPage() {
  const applications = useApplications({ size: 100 });
  const reorderApp = useReorderApplication();
  // null is the create form, a row is that row's editor — the dialog owns every write, so the
  // page only decides which of the two is open.
  const [dialog, setDialog] = React.useState<{ open: boolean; app: Application | null }>({
    open: false,
    app: null,
  });

  const handleReorder = (id: string, status: ApplicationStatus, order: number) => {
    reorderApp.mutate({ id, status, order });
  };

  const openCreate = () => setDialog({ open: true, app: null });
  const openEdit = (app: Application) => setDialog({ open: true, app });

  return (
    <ModuleView
      title="Applications"
      description="Every role in flight. Drag a card to move it through the pipeline, or open one to add notes and a reminder — the dashboard counts follow the same data."
      query={applications}
      emptyHint={{
        title: "Pipeline is empty",
        description: "Track a job from its detail page and it appears here, starting in Saved.",
        action: (
          <Button variant="ai" size="sm" onClick={openCreate}>
            Add application
          </Button>
        ),
      }}
      actions={
        <Button variant="outline" size="sm" onClick={openCreate}>
          <Plus className="size-4 mr-2" aria-hidden />
          Add
        </Button>
      }
    >
      <KanbanBoard
        applications={applications.data?.items ?? []}
        onReorder={handleReorder}
        onOpen={openEdit}
        isPending={reorderApp.isPending}
      />
      <ApplicationDialog
        application={dialog.app}
        open={dialog.open}
        onOpenChange={(open) => setDialog((cur) => ({ ...cur, open }))}
      />
    </ModuleView>
  );
}
