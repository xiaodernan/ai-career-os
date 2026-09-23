"use client";

import * as React from "react";
import { Check, RefreshCw, Save, Sparkles } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ProcessingSteps } from "@/components/ai/processing-steps";
import { TaskProgress, localStages } from "@/components/ai/task-stream";
import { AIBadge } from "@/components/ai/ai-badge";
import { EvidenceList } from "@/components/ai/evidence-list";
import { DiffView } from "@/components/common/diff-view";
import { CopyButton, DownloadButton, SectionHeading } from "@/components/common/export-buttons";
import { StreamingText } from "@/components/ai/streaming-text";
import { useSaveTailoredVersion, useTailorResume, type TailorRun } from "@/lib/hooks/actions";
import { str } from "@/lib/api/normalize";

const STAGES = [
  "Reading your knowledge base",
  "Matching experience to the JD",
  "Rewriting bullets",
  "Checking for invented claims",
];

/**
 * Tailoring panel (§11): runs /ai/tailor, then shows the accepted/rejected diff
 * plus the assembled document with copy/download. Never auto-applied — keeping a
 * draft takes an explicit "save as version", which is the only thing that writes.
 */
export function TailorPanel({
  jobId,
  resumeVersionId,
  resumeLabel,
}: {
  jobId: string;
  resumeVersionId?: string | null;
  resumeLabel?: string;
}) {
  const tailor = useTailorResume(jobId);
  const save = useSaveTailoredVersion(jobId);
  const [result, setResult] = React.useState<TailorRun | null>(null);
  const [saved, setSaved] = React.useState<string | null>(null);
  const [view, setView] = React.useState<"diff" | "document">("diff");

  const run = () => {
    setSaved(null);
    tailor.mutate(resumeVersionId ?? null, { onSuccess: setResult });
  };
  const tailored = result?.tailored;
  const document = tailored?.markdown || tailored?.text || "";
  const error = tailor.error ?? save.error;

  return (
    <Card>
      <CardContent className="space-y-4">
        <SectionHeading
          eyebrow="AI tailoring"
          icon={<Sparkles className="size-4" aria-hidden />}
          title="Tailored resume for this role"
          description={
            resumeLabel
              ? `Rewrites bullets and reorders projects from ${resumeLabel}. Experience is never invented — unsupported claims are rejected and listed.`
              : "Rewrites bullets and reorders projects from your current resume. Experience is never invented."
          }
          action={
            <Button variant="ai" size="sm" onClick={run} loading={tailor.isPending}>
              {result ? <RefreshCw aria-hidden /> : <Sparkles aria-hidden />}
              {result ? "Run again" : "Tailor now"}
            </Button>
          }
        />

        {tailor.isPending && !result && (
          <div className="rounded-lg border border-border/70 bg-muted/30 p-3">
            <ProcessingSteps steps={localStages(STAGES, 1)} />
          </div>
        )}

        {result?.taskId && !tailor.isPending && (
          <TaskProgress taskId={result.taskId} title="Run stream" showTimeline />
        )}

        {error != null && (
          <div role="alert" className="rounded-lg border border-destructive/25 bg-destructive/10 p-3 text-sm text-destructive">
            {error instanceof Error ? error.message : "Tailoring failed."}
          </div>
        )}

        {result && (
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <AIBadge label="Tailored draft" />
              {saved && (
                <Badge variant="success" className="gap-1 text-2xs font-normal">
                  <Check className="size-3" aria-hidden />
                  Saved as {saved}
                </Badge>
              )}
              <div className="ml-auto flex items-center gap-1.5">
                {document && (
                  <>
                    <Button
                      variant={view === "diff" ? "secondary" : "ghost"}
                      size="xs"
                      onClick={() => setView("diff")}
                      aria-pressed={view === "diff"}
                    >
                      Diff
                    </Button>
                    <Button
                      variant={view === "document" ? "secondary" : "ghost"}
                      size="xs"
                      onClick={() => setView("document")}
                      aria-pressed={view === "document"}
                    >
                      Full document
                    </Button>
                    <Button
                      variant="outline"
                      size="xs"
                      loading={save.isPending}
                      disabled={!result}
                      onClick={() =>
                        save.mutate(
                          { raw: result?.raw, plaintext: document, resumeVersionId },
                          { onSuccess: (item) => setSaved(str(item, "label") ?? "version") }
                        )
                      }
                    >
                      <Save aria-hidden />
                      {saved ? "Save again" : "Save as version"}
                    </Button>
                    <CopyButton text={document} />
                    <DownloadButton text={document} filename={`resume-${jobId.slice(0, 8)}.md`} mime="text/markdown;charset=utf-8" />
                  </>
                )}
              </div>
            </div>

            {view === "diff" ? (
              result.diff && (result.diff.accepted.length || result.diff.rejected.length) ? (
                <DiffView
                  accepted={result.diff.accepted}
                  rejected={result.diff.rejected}
                  notes={result.notes}
                  stats={result.stats}
                />
              ) : (
                <p className="text-sm text-muted-foreground">
                  The response carried no structured diff. The document view still shows what was
                  produced.
                </p>
              )
            ) : document ? (
              <StreamingText content={document} className="rounded-lg border border-border/70 bg-muted/20 p-4" />
            ) : (
              <p className="text-sm text-muted-foreground">
                No document text was returned for this run — only the change list above.
              </p>
            )}

            {(result.evidence?.length ?? 0) > 0 && (
              <div className="space-y-2 pt-2">
                <h4 className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
                  Evidence used
                </h4>
                <EvidenceList items={result.evidence ?? []} limit={3} />
              </div>
            )}
          </div>
        )}

        {!result && !tailor.isPending && (
          <p className="text-xs text-muted-foreground">
            Nothing has been generated yet — the draft appears here after you run it, and stays a
            proposal until you export or save it as a version.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
