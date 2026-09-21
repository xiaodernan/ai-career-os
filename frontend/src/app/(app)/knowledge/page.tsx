"use client";

import { Library } from "lucide-react";
import { ModuleView } from "@/components/common/module-view";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useKnowledgeSources } from "@/lib/hooks/resources";

export default function KnowledgePage() {
  const sources = useKnowledgeSources();
  return (
    <ModuleView
      title="Knowledge Base"
      description="Everything the agents can cite: resumes, projects, notes, JDs, company research, feedback."
      query={sources}
      emptyHint={{
        title: "The knowledge base is empty",
        description: "Add sources and they'll be parsed, chunked and embedded for retrieval with citations.",
      }}
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
