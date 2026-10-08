"use client";

import * as React from "react";
import { Plus } from "lucide-react";
import { ModuleView } from "@/components/common/module-view";
import { Pagination } from "@/components/common/pagination";
import { lastPageOf } from "@/lib/page-window";
import { Button } from "@/components/ui/button";
import { useApplication, useApplications } from "@/lib/hooks/resources";
import { useReorderApplication } from "@/lib/hooks/actions";
import { useUrlState } from "@/lib/hooks/use-url-state";
import type { Application, ApplicationStatus } from "@/lib/api/types";
import { KanbanBoard } from "@/components/common/kanban";
import { ApplicationDialog } from "@/components/applications/application-dialog";

// The most rows one request may carry: `Paging.MAX_PAGE_SIZE` on the server, which clamps
// anything larger. Past this many applications the board pages rather than asking for more.
const PAGE_SIZE = 100;

// Module-level so `setUrl` (a `useCallback` keyed on this object) is stable across renders.
const PAGE_DEFAULTS: { application?: string; page: number } = { application: undefined, page: 0 };

export default function ApplicationsPage() {
  // The page index lives in the URL, so a reload or a shared board link opens the same window.
  const [state, setUrl] = useUrlState<{ application?: string; page: number }>(
    PAGE_DEFAULTS,
    { numericKeys: ["page"] }
  );
  const applications = useApplications({ page: state.page, size: PAGE_SIZE });
  const reorderApp = useReorderApplication();
  // null is the create form, a row is that row's editor — the dialog owns every write, so the
  // page only decides which of the two is open.
  const [dialog, setDialog] = React.useState<{ open: boolean; app: Application | null }>({
    open: false,
    app: null,
  });
  // Deep link: the dashboard's attention rows land as `?application=<id>` and open that card's
  // editor. The rows that need attention are the old ones and the board sorts `updatedAt DESC`,
  // so the linked card is exactly the kind the first window cuts off -- when the page in hand
  // does not hold it, the id is fetched on its own instead of the link landing on nothing. The
  // param is cleared on close, so a refetch can never pop the dialog again behind the user's back.
  const deepLinkId = state.application;
  const inPage = deepLinkId
    ? applications.data?.items.find((a) => a.id === deepLinkId)
    : undefined;
  const outside = useApplication(deepLinkId && applications.data && !inPage ? deepLinkId : null);
  React.useEffect(() => {
    // Once the editor is up, later refetches must not re-set it — swapping `application`
    // under an open form would reset whatever the user has typed.
    if (!deepLinkId || dialog.open) return;
    const found = inPage ?? outside.data;
    if (found) setDialog({ open: true, app: found });
  }, [deepLinkId, inPage, outside.data, dialog.open]);

  const handleReorder = (id: string, status: ApplicationStatus, order: number) => {
    reorderApp.mutate({ id, status, order });
  };

  const openCreate = () => setDialog({ open: true, app: null });
  const openEdit = (app: Application) => setDialog({ open: true, app });
  const handleDialogOpenChange = (open: boolean) => {
    setDialog((cur) => ({ ...cur, open }));
    if (!open && state.application) setUrl({ application: undefined });
  };

  const total = applications.data?.total ?? 0;
  // A past-the-end page is an empty window over a real total, not an empty board: the
  // answer's own window is the divisor (`data.size`), so the URL is corrected to the last
  // page that exists -- `lastPageOf` (lib/page-window.ts) is that rule in one place. A
  // layout effect, because the stale commit paints its empty copy first -- React flushes
  // this update before the browser paints, so the wrong screen is replaced, not seen.
  const lastPage = applications.data ? lastPageOf(total, applications.data.size) : 0;
  React.useLayoutEffect(() => {
    if (applications.data && state.page > lastPage) setUrl({ page: lastPage });
  }, [applications.data, state.page, lastPage, setUrl]);

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
      {total > PAGE_SIZE && (
        <Pagination
          page={applications.data?.page ?? state.page}
          size={PAGE_SIZE}
          total={total}
          label="applications"
          onPageChange={(page) => {
            setUrl({ page });
            window.scrollTo({ top: 0, behavior: "smooth" });
          }}
        />
      )}
      <ApplicationDialog
        application={dialog.app}
        open={dialog.open}
        onOpenChange={handleDialogOpenChange}
      />
    </ModuleView>
  );
}
