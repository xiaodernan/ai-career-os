"use client";

import * as React from "react";
import { Library } from "lucide-react";
import { ModuleView } from "@/components/common/module-view";
import { Pagination } from "@/components/common/pagination";
import { lastPageOf } from "@/lib/page-window";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { SourceDeleteButton, SourceUploadCard } from "@/components/knowledge/source-actions";
import { NotesPanel } from "@/components/knowledge/notes-panel";
import { useKnowledgeSources } from "@/lib/hooks/resources";
import { useUrlState } from "@/lib/hooks/use-url-state";
import { useLocale } from "@/lib/i18n/locale-context";
import { knowledgeFocus } from "@/lib/knowledge-focus";

// The route's own default window: `GET /knowledge/sources` binds `size` with
// `defaultValue = "20"`, so this number asks for exactly what the server would have
// chosen anyway -- the hook's own 50 literal never reaches the wire on this path.
const PAGE_SIZE = 20;

export default function KnowledgePage() {
  const { t } = useLocale();
  // `src` is the document a citation points at: the match panel, the copilot's answer and its artifacts
  // all link `/knowledge?src=<documentId>`, which is `document_chunks.document_id` -- the `documents`
  // row the chunks came from, not this list's own `knowledge_sources` id. The narrowing is the
  // backend's, because this page holds one window of sources: filtering what arrived locally could not
  // tell a deleted document from one that simply sits past the window.
  const [state, setUrl] = useUrlState<{ src?: string; page: number }>(
    { src: undefined, page: 0 },
    { numericKeys: ["page"] }
  );
  // A hand-edited `?src=` arrives as the empty string, which `buildUrl` would send as a real parameter
  // the UUID binder has to reject. Blank means "the whole board", which is also what clearing does.
  const src = knowledgeFocus(state.src);
  const showAll = () => setUrl({ src: undefined });
  // Live while anything is still ingesting: the list polls every few seconds until
  // every row reads ready/failed, so an upload visibly moves without a reload.
  const sources = useKnowledgeSources(true, src, { page: state.page, size: PAGE_SIZE });

  const total = sources.data?.total ?? 0;
  // A past-the-end page is an empty window over a real total, not an empty list: the answer's
  // own window is the divisor (`data.size`), so the URL is corrected to the last page that
  // exists -- `lastPageOf` (lib/page-window.ts) is that rule in one place. A layout effect,
  // because the stale commit paints its empty copy first -- React flushes this update before
  // the browser paints, so the wrong screen is replaced, not seen.
  const lastPage = sources.data ? lastPageOf(total, sources.data.size) : 0;
  React.useLayoutEffect(() => {
    if (sources.data && state.page > lastPage) setUrl({ page: lastPage });
  }, [sources.data, state.page, lastPage, setUrl]);

  return (
    <div className="space-y-4">
      {!src && <SourceUploadCard />}
      <ModuleView
      title={t("knowledge.title")}
      description={
        src
          ? "Showing the source one of your citations points at."
          : "Everything the agents can cite: resumes, projects, notes, JDs, company research, feedback."
      }
      query={sources}
      actions={
        src ? (
          <Button variant="outline" size="sm" onClick={showAll}>
            Show all sources
          </Button>
        ) : undefined
      }
      emptyHint={
        src
          ? {
              title: "No source matches that citation",
              description: "The document may have been deleted, or its ingestion never finished.",
              action: (
                <Button variant="outline" size="sm" onClick={showAll}>
                  Show all sources
                </Button>
              ),
            }
          : {
              title: "The knowledge base is empty",
              description:
                "Add sources and they'll be parsed, chunked and embedded for retrieval with citations.",
            }
      }
      ctaHref="/copilot"
      ctaLabel="Ask Copilot to ingest"
      footer={
        !src && total > PAGE_SIZE && (
          <Pagination
            page={sources.data?.page ?? state.page}
            size={PAGE_SIZE}
            total={total}
            label="sources"
            onPageChange={(page) => {
              setUrl({ page });
              window.scrollTo({ top: 0, behavior: "smooth" });
            }}
          />
        )
      }
      renderItem={(s) => (
        <Card key={s.id}>
          <CardContent className="flex items-center gap-3">
            <span className="flex size-9 items-center justify-center rounded-lg bg-muted text-muted-foreground">
              <Library className="size-4.5" aria-hidden />
            </span>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium">{s.title}</p>
              <p className="truncate text-xs text-muted-foreground capitalize">
                {s.kind.replace("_", " ")}
                {s.error && <span className="text-destructive"> · {s.error}</span>}
              </p>
            </div>
            <Badge
              variant={
                s.status === "ready" ? "success" : s.status === "failed" ? "destructive" : s.status === "ingesting" ? "ai" : "secondary"
              }
              className="capitalize"
            >
              {s.status}
            </Badge>
            <SourceDeleteButton id={s.id} title={s.title} />
          </CardContent>
        </Card>
      )}
    />
    {/* Notes live beside the sources, not inside them: a note is its own UserNote row, not an
      ingested document, and the `?src=` citation focus narrows documents only. */}
    {!src && <NotesPanel />}
    </div>
  );
}
