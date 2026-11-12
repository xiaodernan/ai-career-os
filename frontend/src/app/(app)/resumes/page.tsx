"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FileText, FolderSearch, Sparkles, Trash2 } from "lucide-react";
import { PageHeader } from "@/components/common/page-header";
import { GradientText } from "@/components/ui/gradient-text";
import { Pagination } from "@/components/common/pagination";
import { lastPageOf } from "@/lib/page-window";
import { QueryBoundary } from "@/components/common/query-boundary";
import { LoadingListSkeleton } from "@/components/common/loading-skeletons";
import { ConfirmDialog } from "@/components/common/confirm-dialog";
import { UploadDropzone } from "@/components/resumes/upload-dropzone";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useDeleteResume } from "@/lib/hooks/actions";
import { useLocale } from "@/lib/i18n/locale-context";
import { useResumes } from "@/lib/hooks/resources";
import { useUrlState } from "@/lib/hooks/use-url-state";
import { formatDate } from "@/lib/format";
import { useQueryClient } from "@tanstack/react-query";
import { useWarmLink } from "@/lib/hooks/use-warm-link";
import type { Resume } from "@/lib/api/types";

// The route's own default window: `GET /resumes` binds `size` with `defaultValue = "20"`, so
// this number asks for exactly what the server would have chosen anyway.
const PAGE_SIZE = 20;

// Module-level so `setUrl` (a `useCallback` keyed on this object) is stable across renders.
const PAGE_DEFAULTS: { page: number } = { page: 0 };

function statusBadge(
  status: string,
  t: (key: string) => string
): { label: string; variant: "success" | "warning" | "destructive" | "secondary" | "ai" } {
  switch (status) {
    case "parsed":
      return { label: t("resumes.status.parsed"), variant: "success" };
    case "parsing":
      return { label: t("resumes.status.parsing"), variant: "warning" };
    case "failed":
      return { label: t("resumes.status.failed"), variant: "destructive" };
    case "ingesting":
      return { label: t("resumes.status.ingesting"), variant: "ai" };
    default:
      return { label: t("resumes.status.uploaded"), variant: "secondary" };
  }
}

export default function ResumesPage() {
  const { t, locale } = useLocale();
  // The page index lives in the URL, so a reload or a shared list link opens the same window.
  const [state, setUrl] = useUrlState<{ page: number }>(
    PAGE_DEFAULTS,
    { numericKeys: ["page"] }
  );
  const resumes = useResumes({ page: state.page, size: PAGE_SIZE });
  const qc = useQueryClient();
  const router = useRouter();
  const warm = useWarmLink();
  const [pendingDelete, setPendingDelete] = React.useState<Resume | null>(null);
  const del = useDeleteResume();

  const total = resumes.data?.total ?? 0;
  // A past-the-end page is an empty window over a real total, not an empty list: the answer's
  // own window is the divisor (`data.size`), so the URL is corrected to the last page that
  // exists -- `lastPageOf` (lib/page-window.ts) is that rule in one place. A layout effect,
  // because the stale commit paints its empty copy first -- React flushes this update before
  // the browser paints, so the wrong screen is replaced, not seen.
  const lastPage = resumes.data ? lastPageOf(total, resumes.data.size) : 0;
  React.useLayoutEffect(() => {
    if (resumes.data && state.page > lastPage) setUrl({ page: lastPage });
  }, [resumes.data, state.page, lastPage, setUrl]);

  return (
    <div className="mx-auto max-w-4xl space-y-8">
      {/* The resume manager is the first surface a new reader works through -- upload, then
          parse, then versions -- so its header carries the same front-door band the dashboard,
          jobs board and inbox established: static light-theme washes, a dark-only aurora
          (screen-blend over a light Card would wash it white, the trap Epic 137 documented),
          a shimmer hairline and a CSS-only staggered entrance. Every layer is a plain decorated
          span/div, so the band adds zero client JS and leaves the route budget untouched; all
          motion is decorative and `prefers-reduced-motion` stays authoritative via globals.css.
          Unlike those pages this header has no actions (the real work is the dropzone below), so
          there is no CTA to lift here -- the band frames the title, nothing more. */}
      <section className="animate-fade-up relative overflow-hidden rounded-2xl border hairline bg-card/60 shadow-card">
        {/* Light-theme ambient washes: static gradients, zero per-frame cost. */}
        <div
          aria-hidden
          className="pointer-events-none absolute -right-20 -top-24 h-64 w-64 rounded-full"
          style={{
            background:
              "radial-gradient(closest-side, color-mix(in oklch, var(--primary) 16%, transparent), transparent)",
          }}
        />
        <div
          aria-hidden
          className="pointer-events-none absolute -bottom-28 -left-24 h-64 w-64 rounded-full"
          style={{
            background:
              "radial-gradient(closest-side, color-mix(in oklch, var(--primary) 9%, transparent), transparent)",
          }}
        />
        {/* Dark-theme aurora: screen-blend light only ever composited over a dark surface. */}
        <div aria-hidden className="pointer-events-none absolute inset-0 hidden overflow-hidden dark:block">
          <span className="aurora-blob aurora-blob-1 opacity-30" />
          <span className="aurora-blob aurora-blob-2 opacity-30" />
          <div className="aurora-grid opacity-30" />
        </div>
        {/* Shimmer hairline crowns the band -- the same premium separator the dashboard uses. */}
        <span aria-hidden className="shimmer-rule absolute inset-x-0 top-0 block h-px" />
        <div className="relative px-6 py-6">
          <PageHeader
            title={<GradientText className="italic">{t("resumes.title")}</GradientText>}
            description={
              <span className="animate-fade-up block" style={{ animationDelay: "90ms" }}>
                {t("resumes.description")}
              </span>
            }
          />
        </div>
      </section>

      <section aria-label={t("resumes.uploadSection")}>
        <UploadDropzone
          onUploaded={(id) => {
            void qc.invalidateQueries({ queryKey: ["resumes"] });
            if (id) router.push(`/resumes/${id}`);
          }}
        />
      </section>

      <section aria-label={t("resumes.existingSection")} className="space-y-3">
        <h2 className="text-sm font-semibold text-muted-foreground">
          {t("resumes.yourVersions")}
        </h2>
        <QueryBoundary
          query={resumes}
          skeleton={<LoadingListSkeleton rows={3} />}
          empty={{
            icon: <FolderSearch aria-hidden />,
            title: t("resumes.empty"),
            description:
              t("resumes.emptyDescription"),
          }}
          notLive={{
            title: t("common.notLiveTitle"),
            description:
              t("resumes.notLiveDescription"),
          }}
          boxed={false}
        >
          {(page) => (
            <ul className="space-y-3">
              {page.items.map((r) => {
                const badge = statusBadge(r.status, t);
                return (
                  <li key={r.id}>
                    <Card className="transition-shadow duration-200 hover:shadow-pop">
                      <CardContent className="flex flex-wrap items-center gap-3">
                        <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-muted text-muted-foreground">
                          <FileText className="size-5" aria-hidden />
                        </span>
                        <div className="min-w-0 flex-1 basis-52">
                          <Link
                            href={`/resumes/${r.id}`}
                            onMouseEnter={warm(`/resumes/${r.id}`)}
                            onFocus={warm(`/resumes/${r.id}`)}
                            className="truncate text-sm font-medium hover:underline focus-visible:ring-[3px] focus-visible:ring-primary/30 rounded-md"
                          >
                            {r.title}
                          </Link>
                          <p className="mt-0.5 text-xs text-muted-foreground">
                            {r.currentVersionId
                              ? t("resumes.currentVersionSet")
                              : r.status === "parsed"
                                ? t("resumes.parsedOpenToSet")
                                : t("resumes.awaitingParsing")}
                            {r.createdAt ? t("resumes.addedOn", { when: formatDate(r.createdAt, locale) }) : ""}
                          </p>
                        </div>
                        <Badge variant={badge.variant} className="shrink-0 text-2xs font-normal">
                          {badge.label}
                        </Badge>
                        <div className="flex shrink-0 items-center gap-1.5">
                          <Button variant="outline" size="sm" asChild>
                            <Link
                              href={`/resumes/${r.id}`}
                              onMouseEnter={warm(`/resumes/${r.id}`)}
                              onFocus={warm(`/resumes/${r.id}`)}
                            >
                              {t("resumes.open")}
                              <Sparkles aria-hidden />
                            </Link>
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon-sm"
                            aria-label={t("resumes.deleteAria", { title: r.title })}
                            onClick={() => setPendingDelete(r)}
                          >
                            <Trash2 aria-hidden />
                          </Button>
                        </div>
                      </CardContent>
                    </Card>
                  </li>
                );
              })}
            </ul>
          )}
        </QueryBoundary>
        {total > PAGE_SIZE && (
          <Pagination
            page={resumes.data?.page ?? state.page}
            size={PAGE_SIZE}
            total={total}
            label={t("resumes.paginationLabel")}
            onPageChange={(page) => {
              setUrl({ page });
              window.scrollTo({ top: 0, behavior: "smooth" });
            }}
          />
        )}
      </section>

      <ConfirmDialog
        open={pendingDelete != null}
        onOpenChange={(o) => !o && setPendingDelete(null)}
        title={t("resumes.deleteTitle", { title: pendingDelete?.title ?? "" })}
        description={t("resumes.deleteDescription")}
        confirmLabel={t("resumes.deleteResume")}
        destructive
        loading={del.isPending}
        onConfirm={() =>
          pendingDelete &&
          del.mutate(pendingDelete.id, {
            onSettled: () => setPendingDelete(null),
          })
        }
      />
    </div>
  );
}
