"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FileText, FolderSearch, Sparkles, Trash2 } from "lucide-react";
import { PageHeader } from "@/components/common/page-header";
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
import { useResumes } from "@/lib/hooks/resources";
import { useUrlState } from "@/lib/hooks/use-url-state";
import { formatDate } from "@/lib/format";
import { useQueryClient } from "@tanstack/react-query";
import type { Resume } from "@/lib/api/types";

// The route's own default window: `GET /resumes` binds `size` with `defaultValue = "20"`, so
// this number asks for exactly what the server would have chosen anyway.
const PAGE_SIZE = 20;

// Module-level so `setUrl` (a `useCallback` keyed on this object) is stable across renders.
const PAGE_DEFAULTS: { page: number } = { page: 0 };

function statusBadge(status: string): { label: string; variant: "success" | "warning" | "destructive" | "secondary" | "ai" } {
  switch (status) {
    case "parsed":
      return { label: "Structured", variant: "success" };
    case "parsing":
      return { label: "Parsing…", variant: "warning" };
    case "failed":
      return { label: "Failed", variant: "destructive" };
    case "ingesting":
      return { label: "Ingesting…", variant: "ai" };
    default:
      return { label: "Uploaded", variant: "secondary" };
  }
}

export default function ResumesPage() {
  // The page index lives in the URL, so a reload or a shared list link opens the same window.
  const [state, setUrl] = useUrlState<{ page: number }>(
    PAGE_DEFAULTS,
    { numericKeys: ["page"] }
  );
  const resumes = useResumes({ page: state.page, size: PAGE_SIZE });
  const qc = useQueryClient();
  const router = useRouter();
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
      <PageHeader
        title="Resumes"
        description="Every upload is parsed into a structured profile and chunked into the knowledge base the agents cite from. Nothing is scored that isn't in your documents."
      />

      <section aria-label="Upload a resume">
        <UploadDropzone
          onUploaded={(id) => {
            void qc.invalidateQueries({ queryKey: ["resumes"] });
            if (id) router.push(`/resumes/${id}`);
          }}
        />
      </section>

      <section aria-label="Existing resumes" className="space-y-3">
        <h2 className="text-sm font-semibold text-muted-foreground">Your versions</h2>
        <QueryBoundary
          query={resumes}
          skeleton={<LoadingListSkeleton rows={3} />}
          empty={{
            icon: <FolderSearch aria-hidden />,
            title: "No resumes yet",
            description:
              "Drop a file above to get started. The ingestion pipeline extracts experience, projects and skills, then grades resume quality.",
          }}
          notLive={{
            title: "This API build has no resume list",
            description:
              "GET /resumes answered 404, so this frontend and the backend it is talking to are different versions. Uploads are wired and appear as soon as they match — nothing is invented to fill the gap.",
          }}
          boxed={false}
        >
          {(page) => (
            <ul className="space-y-3">
              {page.items.map((r) => {
                const badge = statusBadge(r.status);
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
                            className="truncate text-sm font-medium hover:underline focus-visible:ring-[3px] focus-visible:ring-primary/30 rounded-md"
                          >
                            {r.title}
                          </Link>
                          <p className="mt-0.5 text-xs text-muted-foreground">
                            {r.currentVersionId
                              ? "Current version set · agents match against it"
                              : r.status === "parsed"
                                ? "Parsed — open to set the current version"
                                : "Awaiting parsing"}
                            {r.createdAt ? ` · added ${formatDate(r.createdAt)}` : ""}
                          </p>
                        </div>
                        <Badge variant={badge.variant} className="shrink-0 text-2xs font-normal">
                          {badge.label}
                        </Badge>
                        <div className="flex shrink-0 items-center gap-1.5">
                          <Button variant="outline" size="sm" asChild>
                            <Link href={`/resumes/${r.id}`}>
                              Open
                              <Sparkles aria-hidden />
                            </Link>
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon-sm"
                            aria-label={`Delete ${r.title}`}
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
            label="resumes"
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
        title={`Delete “${pendingDelete?.title ?? ""}”?`}
        description="The resume and its versions are removed from your workspace. Knowledge chunks ingested from it stop being cited."
        confirmLabel="Delete resume"
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
