"use client";

import * as React from "react";
import { FileText, RefreshCw, Sparkles } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { ProcessingSteps } from "@/components/ai/processing-steps";
import { AIBadge } from "@/components/ai/ai-badge";
import dynamic from "next/dynamic";
import { EvidenceList } from "@/components/ai/evidence-list";
import { CopyButton, DownloadButton, SectionHeading } from "@/components/common/export-buttons";
import { localStages } from "@/components/ai/task-stream";
import { useCoverLetter } from "@/lib/hooks/actions";
import { normalizeEvidence } from "@/lib/api/normalize";
import { ApiError } from "@/lib/api/client";
import { missingEndpointMessage } from "@/lib/api/missing-endpoint";
import { useLocale } from "@/lib/i18n/locale-context";
import type { Evidence } from "@/lib/api/types";

/* Code-split, not a static import: StreamingText carries the react-markdown
 * stack, and this panel only renders it after the user starts a generation —
 * there is no reason for the job detail page's first load to pay for it. */
const StreamingText = dynamic(() =>
  import("@/components/ai/streaming-text").then((m) => m.StreamingText)
);

const STAGE_KEYS = [
  "coverLetter.stages.readingJd",
  "coverLetter.stages.pullingContext",
  "coverLetter.stages.drafting",
  "coverLetter.stages.checkingClaims",
];

const TONES = [
  { value: "balanced", labelKey: "coverLetter.tones.balanced" },
  { value: "formal", labelKey: "coverLetter.tones.formal" },
  { value: "concise", labelKey: "coverLetter.tones.concise" },
  { value: "confident", labelKey: "coverLetter.tones.confident" },
];

const LENGTHS = [
  { value: "short", labelKey: "coverLetter.lengths.short" },
  { value: "standard", labelKey: "coverLetter.lengths.standard" },
  { value: "detailed", labelKey: "coverLetter.lengths.detailed" },
];

/**
 * Cover letter panel (§12): generate with tone/length knobs, regenerate, copy,
 * download. Output is markdown-rendered and evidence-cited where the backend
 * supplies citations.
 */
export function CoverLetterPanel({ jobId, resumeVersionId }: { jobId: string; resumeVersionId?: string | null }) {
  const { t } = useLocale();
  const [tone, setTone] = React.useState("balanced");
  const [length, setLength] = React.useState("standard");
  const mutation = useCoverLetter(jobId);
  const [result, setResult] = React.useState<{ text: string; evidence: unknown } | null>(null);

  const run = () =>
    mutation.mutate({ resumeVersionId, tone, length }, { onSuccess: (d) => setResult({ text: d.text, evidence: d.evidence }) });

  const evidence: Evidence[] = result ? normalizeEvidence(result.evidence) : [];
  const error = mutation.error;

  return (
    <Card>
      <CardContent className="space-y-4">
        <SectionHeading
          eyebrow={t("coverLetter.eyebrow")}
          icon={<FileText className="size-4" aria-hidden />}
          title={t("coverLetter.title")}
          description={t("coverLetter.description")}
          action={
            <Button variant="ai" size="sm" onClick={run} loading={mutation.isPending}>
              {result ? <RefreshCw aria-hidden /> : <Sparkles aria-hidden />}
              {result ? t("coverLetter.regenerate") : t("coverLetter.generate")}
            </Button>
          }
        />

        <div className="flex flex-wrap items-end gap-3">
          <div className="space-y-1.5">
            <Label htmlFor="cl-tone">{t("coverLetter.tone")}</Label>
            <Select value={tone} onValueChange={setTone}>
              <SelectTrigger id="cl-tone" size="sm" className="w-40">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {TONES.map((t2) => (
                  <SelectItem key={t2.value} value={t2.value}>
                    {t(t2.labelKey)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="cl-length">{t("coverLetter.length")}</Label>
            <Select value={length} onValueChange={setLength}>
              <SelectTrigger id="cl-length" size="sm" className="w-44">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {LENGTHS.map((l) => (
                  <SelectItem key={l.value} value={l.value}>
                    {t(l.labelKey)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        {mutation.isPending && !result && (
          <div className="rounded-lg border border-border/70 bg-muted/30 p-3">
            <ProcessingSteps steps={localStages(STAGE_KEYS.map((k) => t(k)), 1)} />
          </div>
        )}

        {error != null && (
          <div role="alert" className="rounded-lg border border-destructive/25 bg-destructive/10 p-3 text-sm text-destructive">
            {error instanceof ApiError && error.isNotFound
              ? missingEndpointMessage("POST /jobs/{id}/cover-letter")
              : error instanceof Error
                ? error.message
                : t("coverLetter.generationFailed")}
          </div>
        )}

        {result && (
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <AIBadge label={t("coverLetter.draftBadge")} />
              <span className="text-xs text-muted-foreground tabular-nums">
                {result.text
                  ? t("coverLetter.words", { count: result.text.trim().split(/\s+/).length })
                  : ""}
              </span>
              <div className="ml-auto flex gap-1.5">
                <CopyButton text={result.text} label={t("coverLetter.copyLetter")} />
                <DownloadButton
                  text={result.text}
                  filename={`cover-letter-${jobId.slice(0, 8)}.md`}
                  mime="text/markdown;charset=utf-8"
                  label={t("coverLetter.download")}
                />
              </div>
            </div>
            {result.text ? (
              <StreamingText content={result.text} className="rounded-lg border border-border/70 bg-muted/20 p-4" />
            ) : (
              <p className="text-sm text-muted-foreground">
                {t("coverLetter.noLetterText")}
              </p>
            )}
            {evidence.length > 0 && <EvidenceList items={evidence} limit={2} dense />}
          </div>
        )}

        {!result && !mutation.isPending && (
          <p className="text-xs text-muted-foreground">{t("coverLetter.noLetterYet")}</p>
        )}
      </CardContent>
    </Card>
  );
}
