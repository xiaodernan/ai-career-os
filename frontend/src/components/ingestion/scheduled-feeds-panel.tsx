"use client";

import * as React from "react";
import { CalendarClock, Play, Plus, Trash2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/common/confirm-dialog";
import { Pagination } from "@/components/common/pagination";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { relativeTime } from "@/lib/format";
import { lastPageOf } from "@/lib/page-window";
import { useLocale } from "@/lib/i18n/locale-context";
import { useUrlState } from "@/lib/hooks/use-url-state";
import {
  useCreateIngestionFeed,
  useDeleteIngestionFeed,
  useRunIngestionFeed,
  useToggleIngestionFeed,
} from "@/lib/hooks/ingestion";
import {
  useIngestionFeeds,
  useIngestionRunDetail,
  useIngestionRuns,
} from "@/lib/hooks/resources";
import type { IngestionFeed, IngestionRun } from "@/lib/api/types";

/**
 * The feeds the backend's clock sweeps (roadmap 19.2).
 *
 * The panel is the browser's half of a feature whose other half runs at 03:20:
 * a feed is a URL plus a switch, and every pull leaves a run the reader can
 * open. A failed pull is shown as the run it is — the reason the server wrote
 * down — rather than as an error state, because the sweep already turned it
 * into a record.
 *
 * Applying a plan is deliberately absent: a run is a proposal, and the board
 * is only written through the reviewable ingestion path above.
 */

// The route's own default window: `GET /ingestion/runs` binds `size` with
// `defaultValue = "20"`, so this number asks for exactly what the server would have
// chosen anyway -- the hook's own 20 literal never reaches the wire on this path.
const PAGE_SIZE = 20;

// `rpage` rather than the page's own `page`: the panel is one list on a screen that
// may grow another, and two lists on one screen need two questions.
const PAGE_DEFAULTS: { rpage: number } = { rpage: 0 };

/** The titles a stored plan proposes to create, read defensively from the engine's map. */
export function planTitles(plan: Record<string, unknown> | null | undefined): string[] {
  const rows = plan?.create;
  if (!Array.isArray(rows)) return [];
  return rows
    .map((row) =>
      row && typeof row === "object" ? (row as { title?: unknown }).title : undefined
    )
    .filter((title): title is string => typeof title === "string" && title.trim() !== "");
}

function RunCounts({ run }: { run: IngestionRun }) {
  const { t } = useLocale();
  const counts = run.counts;
  if (!counts) return null;
  return (
    <span className="flex flex-wrap items-center gap-1.5">
      {counts.incoming != null && (
        <Badge variant="outline">{t("ingestion.incomingBadge", { count: counts.incoming })}</Badge>
      )}
      {counts.create != null && (
        <Badge variant="success">{t("ingestion.createBadge", { count: counts.create })}</Badge>
      )}
      {counts.update != null && (
        <Badge variant="outline">{t("ingestion.updateBadge", { count: counts.update })}</Badge>
      )}
      {counts.duplicates != null && (
        <Badge variant="outline">{t("ingestion.duplicateBadge", { count: counts.duplicates })}</Badge>
      )}
      {counts.close != null && (
        <Badge variant="warning">{t("ingestion.closeBadge", { count: counts.close })}</Badge>
      )}
    </span>
  );
}

export function ScheduledFeedsPanel() {
  const { t, locale } = useLocale();
  const feeds = useIngestionFeeds();
  // The run index lives in the URL, so a reload or a shared link opens the same window.
  const [runPage, setRunPage] = useUrlState<{ rpage: number }>(
    PAGE_DEFAULTS,
    { numericKeys: ["rpage"] }
  );
  const runs = useIngestionRuns({ page: runPage.rpage, size: PAGE_SIZE });
  const create = useCreateIngestionFeed();
  const toggle = useToggleIngestionFeed();
  const remove = useDeleteIngestionFeed();
  const runNow = useRunIngestionFeed();

  const [name, setName] = React.useState("");
  const [url, setUrl] = React.useState("");
  const [source, setSource] = React.useState("");
  const [pendingDelete, setPendingDelete] = React.useState<IngestionFeed | null>(null);
  const [openRun, setOpenRun] = React.useState<string | null>(null);
  const detail = useIngestionRunDetail(openRun);

  const addFeed = (event: React.FormEvent) => {
    event.preventDefault();
    const trimmedName = name.trim();
    const trimmedUrl = url.trim();
    if (!trimmedName || !trimmedUrl || create.isPending) return;
    create.mutate(
      { name: trimmedName, url: trimmedUrl, source: source.trim() || undefined },
      {
        onSuccess: () => {
          setName("");
          setUrl("");
          setSource("");
        },
      }
    );
  };

  const feedRows = feeds.data ?? [];
  const runRows = runs.data?.items ?? [];
  const total = runs.data?.total ?? 0;
  // A past-the-end page is an empty window over a real total, not an empty list: the answer's
  // own window is the divisor (`data.size`), so the URL is corrected to the last page that
  // exists -- `lastPageOf` (lib/page-window.ts) is that rule in one place. A layout effect,
  // because the stale commit paints its empty copy first.
  const lastPage = runs.data ? lastPageOf(total, runs.data.size) : 0;
  React.useLayoutEffect(() => {
    if (runs.data && runPage.rpage > lastPage) setRunPage({ rpage: lastPage });
  }, [runs.data, runPage.rpage, lastPage, setRunPage]);
  const titles = planTitles(detail.data?.plan);

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">{t("ingestion.scheduleHeading")}</CardTitle>
          <CardDescription>{t("ingestion.scheduleDescription")}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <form onSubmit={addFeed} className="space-y-3">
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label htmlFor="feed-name">{t("ingestion.feedName")}</Label>
                <Input
                  id="feed-name"
                  value={name}
                  maxLength={120}
                  onChange={(e) => setName(e.target.value)}
                  placeholder={t("ingestion.feedNamePlaceholder")}
                  autoComplete="off"
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="feed-url">{t("ingestion.feedUrl")}</Label>
                <Input
                  id="feed-url"
                  value={url}
                  maxLength={2048}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder={t("ingestion.feedUrlPlaceholder")}
                  autoComplete="off"
                />
              </div>
            </div>
            <div className="flex items-end gap-3">
              <div className="w-40 space-y-1.5">
                <Label htmlFor="feed-source">{t("ingestion.feedSource")}</Label>
                <Input
                  id="feed-source"
                  value={source}
                  maxLength={40}
                  onChange={(e) => setSource(e.target.value)}
                  placeholder={t("ingestion.feedSourcePlaceholder")}
                  autoComplete="off"
                />
              </div>
              <Button
                type="submit"
                size="sm"
                loading={create.isPending}
                disabled={!name.trim() || !url.trim()}
              >
                <Plus aria-hidden />
                {t("ingestion.addFeed")}
              </Button>
            </div>
          </form>

          {feedRows.length > 0 ? (
            <ul className="space-y-2">
              {feedRows.map((feed) => (
                <li key={feed.id} className="space-y-1.5 rounded-lg border border-border/70 p-3">
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium">{feed.name}</p>
                      <p className="truncate text-xs text-muted-foreground">{feed.url}</p>
                    </div>
                    <div className="flex shrink-0 items-center gap-1.5">
                      <Badge variant="outline">{feed.source}</Badge>
                      <Switch
                        checked={feed.enabled}
                        aria-label={t("ingestion.toggleAria", { name: feed.name })}
                        onCheckedChange={(enabled) => toggle.mutate({ id: feed.id, enabled })}
                      />
                      <Button
                        size="sm"
                        variant="outline"
                        loading={runNow.isPending && runNow.variables === feed.id}
                        onClick={() => runNow.mutate(feed.id)}
                      >
                        <Play aria-hidden />
                        {t("ingestion.runNow")}
                      </Button>
                      <Button
                        size="icon"
                        variant="ghost"
                        aria-label={t("ingestion.deleteFeedAria", { name: feed.name })}
                        onClick={() => setPendingDelete(feed)}
                      >
                        <Trash2 aria-hidden />
                      </Button>
                    </div>
                  </div>
                  <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
                    <CalendarClock className="size-3" aria-hidden />
                    {feed.lastRun
                      ? `${t("ingestion.lastRun")} · ${
                          feed.lastRun.status === "failed"
                            ? t("ingestion.statusFailed")
                            : t("ingestion.statusCompleted")
                        } · ${relativeTime(feed.lastRun.startedAt, locale)}`
                      : t("ingestion.neverRun")}
                  </p>
                </li>
              ))}
            </ul>
          ) : feeds.isSuccess ? (
            <p className="text-sm text-muted-foreground">{t("ingestion.noFeeds")}</p>
          ) : feeds.isError ? (
            <p className="text-sm text-muted-foreground">{t("ingestion.feedsUnavailable")}</p>
          ) : null}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">{t("ingestion.runsHeading")}</CardTitle>
          <CardDescription>{t("ingestion.runsDescription")}</CardDescription>
        </CardHeader>
        <CardContent>
          {runRows.length > 0 ? (
            <ul className="space-y-2">
              {runRows.map((run) => (
                <li key={run.id} className="rounded-lg border border-border/70 p-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex min-w-0 items-center gap-2">
                      <Badge variant={run.status === "failed" ? "destructive" : "success"}>
                        {run.status === "failed"
                          ? t("ingestion.statusFailed")
                          : t("ingestion.statusCompleted")}
                      </Badge>
                      <span className="truncate text-sm font-medium">
                        {run.feedName || t("ingestion.unnamedFeed")}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        {relativeTime(run.startedAt, locale)}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <RunCounts run={run} />
                      {run.status !== "failed" && (
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => setOpenRun(openRun === run.id ? null : run.id)}
                        >
                          {openRun === run.id ? t("ingestion.hidePlan") : t("ingestion.viewPlan")}
                        </Button>
                      )}
                    </div>
                  </div>
                  {run.error && <p className="mt-1 text-xs text-danger">{run.error}</p>}
                  {openRun === run.id && (
                    <div className="mt-2 space-y-2 rounded-md bg-muted/40 p-2.5">
                      {detail.isPending ? (
                        <p className="text-xs text-muted-foreground">{t("ingestion.planLoading")}</p>
                      ) : titles.length > 0 ? (
                        <ul className="space-y-1 text-xs text-muted-foreground">
                          {titles.slice(0, 8).map((title, index) => (
                            <li key={`${title}-${index}`}>{title}</li>
                          ))}
                        </ul>
                      ) : (
                        <p className="text-xs text-muted-foreground">{t("ingestion.planEmpty")}</p>
                      )}
                    </div>
                  )}
                </li>
              ))}
            </ul>
          ) : runs.isSuccess ? (
            <p className="text-sm text-muted-foreground">{t("ingestion.noRuns")}</p>
          ) : runs.isError ? (
            <p className="text-sm text-muted-foreground">{t("ingestion.runsUnavailable")}</p>
          ) : null}
          {total > PAGE_SIZE && (
            <div className="mt-4 flex justify-end">
              <Pagination
                page={runs.data?.page ?? runPage.rpage}
                size={PAGE_SIZE}
                total={total}
                label={t("ingestion.runsPaginationLabel")}
                onPageChange={(next) => {
                  setRunPage({ rpage: next });
                  window.scrollTo({ top: 0, behavior: "smooth" });
                }}
              />
            </div>
          )}
        </CardContent>
      </Card>

      <ConfirmDialog
        open={pendingDelete != null}
        onOpenChange={(open) => {
          if (!open) setPendingDelete(null);
        }}
        title={t("ingestion.deleteFeedTitle")}
        description={
          pendingDelete
            ? t("ingestion.deleteFeedDescription", { name: pendingDelete.name })
            : undefined
        }
        confirmLabel={t("ingestion.deleteFeedConfirm")}
        cancelLabel={t("common.cancel")}
        destructive
        loading={remove.isPending}
        onConfirm={() => {
          if (!pendingDelete) return;
          remove.mutate(pendingDelete.id, {
            onSuccess: () => setPendingDelete(null),
          });
        }}
      />
    </div>
  );
}
