"use client";

import { Library } from "lucide-react";
import { ModuleView } from "@/components/common/module-view";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useKnowledgeSources } from "@/lib/hooks/resources";
import { useUrlState } from "@/lib/hooks/use-url-state";
import { knowledgeFocus } from "@/lib/knowledge-focus";

export default function KnowledgePage() {
  // `src` is the document a citation points at: the match panel, the copilot's answer and its artifacts
  // all link `/knowledge?src=<documentId>`, which is `document_chunks.document_id` -- the `documents`
  // row the chunks came from, not this list's own `knowledge_sources` id. The narrowing is the
  // backend's, because this page holds one window of sources: filtering what arrived locally could not
  // tell a deleted document from one that simply sits past the window.
  const [state, setUrl] = useUrlState<{ src?: string }>({ src: undefined });
  // A hand-edited `?src=` arrives as the empty string, which `buildUrl` would send as a real parameter
  // the UUID binder has to reject. Blank means "the whole board", which is also what clearing does.
  const src = knowledgeFocus(state.src);
  const showAll = () => setUrl({ src: undefined });
  const sources = useKnowledgeSources(false, src);

  return (
    <ModuleView
      title="Knowledge Base"
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
          </CardContent>
        </Card>
      )}
    />
  );
}
