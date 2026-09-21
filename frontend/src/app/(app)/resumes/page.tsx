"use client";

import Link from "next/link";
import { FileText } from "lucide-react";
import { ModuleView } from "@/components/common/module-view";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useResumes } from "@/lib/hooks/resources";

export default function ResumesPage() {
  const resumes = useResumes();
  return (
    <ModuleView
      title="Resumes"
      description="Versions and structured profile parsed into queryable experience, projects and skills."
      query={resumes}
      emptyHint={{
        title: "No resumes yet",
        description: "Upload a resume and the ingestion pipeline chunks it into your citable knowledge base.",
      }}
      actions={
        <Button variant="ai" size="sm" asChild>
          <Link href="/copilot">
            <FileText aria-hidden />
            Analyze with Copilot
          </Link>
        </Button>
      }
      renderItem={(r) => (
        <Card key={r.id}>
          <CardContent className="flex items-center gap-3">
            <span className="flex size-9 items-center justify-center rounded-lg bg-muted text-muted-foreground">
              <FileText className="size-4.5" aria-hidden />
            </span>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium">{r.title}</p>
              <p className="text-xs text-muted-foreground">
                {r.currentVersionId ? "Structured profile available" : "Awaiting parse"} ·{" "}
                {r.createdAt ? new Date(r.createdAt).toLocaleDateString() : ""}
              </p>
            </div>
            <Badge
              variant={r.status === "parsed" ? "success" : r.status === "failed" ? "destructive" : "secondary"}
              className="capitalize"
            >
              {r.status}
            </Badge>
          </CardContent>
        </Card>
      )}
    />
  );
}
