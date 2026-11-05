"use client";

import * as React from "react";
import { Plus, Search } from "lucide-react";
import { ModuleView } from "@/components/common/module-view";
import { Pagination } from "@/components/common/pagination";
import { lastPageOf } from "@/lib/page-window";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useApplication, useApplications } from "@/lib/hooks/resources";
import { useReorderApplication } from "@/lib/hooks/actions";
import { useUrlState } from "@/lib/hooks/use-url-state";
import { useLocale } from "@/lib/i18n/locale-context";
import type { Application, ApplicationStatus } from "@/lib/api/types";
import { KanbanBoard } from "@/components/common/kanban";
import { ApplicationDialog } from "@/components/applications/application-dialog";

// The most rows one request may carry: `Paging.MAX_PAGE_SIZE` on the server, which clamps
// anything larger. Past this many applications the board pages rather than asking for more.
const PAGE_SIZE = 100;

// Module-level so `setUrl` (a `useCallback` keyed on this object) is stable across renders.
// `q` is declared here even though it is usually absent: `useUrlState` hydrates by walking
// these keys, so a word left out of the defaults is a word a pasted link cannot restore.
const PAGE_DEFAULTS: { application?: string; page: number; q?: string } = {
  application: undefined,
  page: 0,
  q: undefined,
};

export default function ApplicationsPage() {
  const { t } = useLocale();
  // The page index and the words both live in the URL, so a reload or a shared board link opens
  // the same window of the same question -- the rule the replies board set (49.1) and the company
  // board follows (58.2).
  const [state, setUrl] = useUrlState<{ application?: string; page: number; q?: string }>(
    PAGE_DEFAULTS,
    { numericKeys: ["page"] }
  );
  // The box holds what the reader is typing; the page holds what was asked. A card is a thing a
  // reader edits, so the two must not be the same state: half-typed words would otherwise refetch
  // the board -- and drop a drag's column out from under it -- on every keystroke.
  const [draft, setDraft] = React.useState(state.q ?? "");
  React.useEffect(() => setDraft(state.q ?? ""), [state.q]);
  const ask = (value: string) => setUrl({ q: value.trim() || undefined, page: 0 });
  const applications = useApplications({ page: state.page, size: PAGE_SIZE, q: state.q });
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
      title={t("applications.title")}
      description={t("applications.description")}
      query={applications}
      // Two different empties (49.2): a pipeline nobody has started, and a pipeline full of cards
      // none of which spells the word the reader typed. The second one's way out is the box, not a
      // button that opens a create form -- the reader was not trying to add a card.
      emptyHint={
        state.q
          ? {
              title: t("applications.noMatch", { query: state.q }),
              description: t("applications.noMatchDescription"),
              action: (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setDraft("");
                    ask("");
                  }}
                >
                  {t("applications.clearSearch")}
                </Button>
              ),
            }
          : {
              title: t("applications.pipelineIsEmpty"),
              description: t("applications.pipelineIsEmptyDescription"),
              action: (
                <Button variant="ai" size="sm" onClick={openCreate}>
                  {t("applications.addApplication")}
                </Button>
              ),
            }
      }
      actions={
        <div className="flex flex-wrap items-center justify-end gap-2">
          {/* The question the route has always been able to answer (70.1) and this board never
              asked. It is the server's search rather than a filter over the rows in hand: the pager
              counts the matches, so page two of a word is the second page of the matches -- and the
              words are read as characters, which is what lets a card whose company really carries an
              underscore be found by spelling it. */}
          <form
            role="search"
            className="flex items-center gap-2"
            onSubmit={(event) => {
              event.preventDefault();
              ask(draft);
            }}
          >
            <div className="relative">
              <Search
                aria-hidden
                className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground"
              />
              <Input
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                placeholder={t("applications.searchPlaceholder")}
                aria-label={t("applications.searchLabel")}
                autoComplete="off"
                className="w-40 pl-9 sm:w-60"
              />
            </div>
            <Button type="submit" size="sm" variant="outline">
              {t("chrome.search")}
            </Button>
            {state.q ? (
              <Button
                type="button"
                size="sm"
                variant="ghost"
                onClick={() => {
                  setDraft("");
                  ask("");
                }}
              >
                {t("applications.clearSearch")}
              </Button>
            ) : null}
          </form>
          <Button variant="outline" size="sm" onClick={openCreate}>
            <Plus className="size-4 mr-2" aria-hidden />
            {t("applications.add")}
          </Button>
        </div>
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
          label={t("applications.paginationLabel")}
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
