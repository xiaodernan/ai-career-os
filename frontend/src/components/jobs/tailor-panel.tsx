"use client";

import * as React from "react";
import { Check, Printer, RefreshCw, Save, Sparkles } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ProcessingSteps } from "@/components/ai/processing-steps";
import { localStages } from "@/components/ai/task-stream";
import { AIBadge } from "@/components/ai/ai-badge";
import { EvidenceList } from "@/components/ai/evidence-list";
import { DiffView } from "@/components/common/diff-view";
import { CopyButton, DownloadButton, SectionHeading } from "@/components/common/export-buttons";
import dynamic from "next/dynamic";
import { usePrintResumeVersion, useSaveTailoredVersion, useTailorResume, type TailorRun } from "@/lib/hooks/actions";
import { str } from "@/lib/api/normalize";
import { useLocale } from "@/lib/i18n/locale-context";

/* Code-split, not a static import: StreamingText carries the react-markdown
 * stack, and this panel only renders it after the user starts a tailor run —
 * there is no reason for the job detail page's first load to pay for it. */
const StreamingText = dynamic(() =>
  import("@/components/ai/streaming-text").then((m) => m.StreamingText)
);

const STAGE_KEYS = [
  "tailor.stages.readingKnowledge",
  "tailor.stages.matchingExperience",
  "tailor.stages.rewritingBullets",
  "tailor.stages.checkingClaims",
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
  const print = usePrintResumeVersion();
  const { t } = useLocale();
  const [result, setResult] = React.useState<TailorRun | null>(null);
  const [saved, setSaved] = React.useState<string | null>(null);
  const [savedId, setSavedId] = React.useState<string | null>(null);
  const [view, setView] = React.useState<"diff" | "document">("diff");

  const run = () => {
    setSaved(null);
    setSavedId(null);
    tailor.mutate(resumeVersionId ?? null, { onSuccess: setResult });
  };
  const tailored = result?.tailored;
  const document = tailored?.markdown || "";
  const error = tailor.error ?? save.error;

  return (
    <Card>
      <CardContent className="space-y-4">
        <SectionHeading
          eyebrow={t("tailor.eyebrow")}
          icon={<Sparkles className="size-4" aria-hidden />}
          title={t("tailor.title")}
          description={
            resumeLabel
              ? `${t("tailor.descriptionWith", { resume: resumeLabel })} ${t("tailor.neverInvented")} ${t("tailor.claimsKeptOut")}`
              : `${t("tailor.description")} ${t("tailor.neverInvented")}.`
          }
          action={
            <Button variant="ai" size="sm" onClick={run} loading={tailor.isPending}>
              {result ? <RefreshCw aria-hidden /> : <Sparkles aria-hidden />}
              {result ? t("tailor.runAgain") : t("tailor.tailorNow")}
            </Button>
          }
        />

        {tailor.isPending && !result && (
          <div className="rounded-lg border border-border/70 bg-muted/30 p-3">
            <ProcessingSteps steps={localStages(STAGE_KEYS.map((k) => t(k)), 1)} />
          </div>
        )}

        {error != null && (
          <div role="alert" className="rounded-lg border border-destructive/25 bg-destructive/10 p-3 text-sm text-destructive">
            {error instanceof Error ? error.message : t("tailor.failed")}
          </div>
        )}

        {result && (
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <AIBadge label={t("tailor.draftBadge")} />
              {saved && (
                <Badge variant="success" className="gap-1 text-2xs font-normal">
                  <Check className="size-3" aria-hidden />
                  {t("tailor.savedAs", { name: saved })}
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
                      {t("tailor.diff")}
                    </Button>
                    <Button
                      variant={view === "document" ? "secondary" : "ghost"}
                      size="xs"
                      onClick={() => setView("document")}
                      aria-pressed={view === "document"}
                    >
                      {t("tailor.fullDocument")}
                    </Button>
                    <Button
                      variant="outline"
                      size="xs"
                      loading={save.isPending}
                      disabled={!result}
                      onClick={() =>
                        save.mutate(
                          { raw: result?.raw, plaintext: document, resumeVersionId },
                          {
                            onSuccess: (item) => {
                              setSaved(str(item, "label") ?? "version");
                              setSavedId(str(item, "id") ?? null);
                            },
                          }
                        )
                      }
                    >
                      <Save aria-hidden />
                      {saved ? t("tailor.saveAgain") : t("tailor.saveAsVersion")}
                    </Button>
                    {savedId && (
                      <Button
                        variant="outline"
                        size="xs"
                        loading={print.isPending}
                        onClick={() => print.mutate(savedId)}
                      >
                        <Printer aria-hidden />
                        {t("tailor.printVersion")}
                      </Button>
                    )}
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
                  {t("tailor.noStructuredDiff")}
                </p>
              )
            ) : document ? (
              <StreamingText content={document} className="rounded-lg border border-border/70 bg-muted/20 p-4" />
            ) : (
              <p className="text-sm text-muted-foreground">
                {t("tailor.noDocumentText")}
              </p>
            )}

            {(result.evidence?.length ?? 0) > 0 && (
              <div className="space-y-2 pt-2">
                <h4 className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
                  {t("tailor.evidenceUsed")}
                </h4>
                <EvidenceList items={result.evidence ?? []} limit={3} />
              </div>
            )}
          </div>
        )}

        {!result && !tailor.isPending && (
          <p className="text-xs text-muted-foreground">
            {t("tailor.nothingGeneratedYet")}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
