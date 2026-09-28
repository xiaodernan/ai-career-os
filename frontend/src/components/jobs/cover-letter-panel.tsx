"use client";

import * as React from "react";
import { FileText, RefreshCw, Sparkles } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { ProcessingSteps } from "@/components/ai/processing-steps";
import { AIBadge } from "@/components/ai/ai-badge";
import { StreamingText } from "@/components/ai/streaming-text";
import { EvidenceList } from "@/components/ai/evidence-list";
import { CopyButton, DownloadButton, SectionHeading } from "@/components/common/export-buttons";
import { localStages } from "@/components/ai/task-stream";
import { useCoverLetter } from "@/lib/hooks/actions";
import { normalizeEvidence } from "@/lib/api/normalize";
import { ApiError } from "@/lib/api/client";
import { missingEndpointMessage } from "@/lib/api/missing-endpoint";
import type { Evidence } from "@/lib/api/types";

const STAGES = ["Reading the JD", "Pulling company context", "Drafting", "Checking claims"];

const TONES = [
  { value: "balanced", label: "Balanced" },
  { value: "formal", label: "Formal" },
  { value: "concise", label: "Concise" },
  { value: "confident", label: "Confident" },
];

const LENGTHS = [
  { value: "short", label: "Short (~180 words)" },
  { value: "standard", label: "Standard (~300 words)" },
  { value: "detailed", label: "Detailed (~450 words)" },
];

/**
 * Cover letter panel (§12): generate with tone/length knobs, regenerate, copy,
 * download. Output is markdown-rendered and evidence-cited where the backend
 * supplies citations.
 */
export function CoverLetterPanel({ jobId, resumeVersionId }: { jobId: string; resumeVersionId?: string | null }) {
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
          eyebrow="AI writing"
          icon={<FileText className="size-4" aria-hidden />}
          title="Cover letter"
          description="Built from your resume evidence, the JD and company context. Regenerate with a different tone or length at any time."
          action={
            <Button variant="ai" size="sm" onClick={run} loading={mutation.isPending}>
              {result ? <RefreshCw aria-hidden /> : <Sparkles aria-hidden />}
              {result ? "Regenerate" : "Generate"}
            </Button>
          }
        />

        <div className="flex flex-wrap items-end gap-3">
          <div className="space-y-1.5">
            <Label htmlFor="cl-tone">Tone</Label>
            <Select value={tone} onValueChange={setTone}>
              <SelectTrigger id="cl-tone" size="sm" className="w-40">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {TONES.map((t) => (
                  <SelectItem key={t.value} value={t.value}>
                    {t.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="cl-length">Length</Label>
            <Select value={length} onValueChange={setLength}>
              <SelectTrigger id="cl-length" size="sm" className="w-44">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {LENGTHS.map((l) => (
                  <SelectItem key={l.value} value={l.value}>
                    {l.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        {mutation.isPending && !result && (
          <div className="rounded-lg border border-border/70 bg-muted/30 p-3">
            <ProcessingSteps steps={localStages(STAGES, 1)} />
          </div>
        )}

        {error != null && (
          <div role="alert" className="rounded-lg border border-destructive/25 bg-destructive/10 p-3 text-sm text-destructive">
            {error instanceof ApiError && error.isNotFound
              ? missingEndpointMessage("POST /jobs/{id}/cover-letter")
              : error instanceof Error
                ? error.message
                : "Generation failed."}
          </div>
        )}

        {result && (
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <AIBadge label="Draft" />
              <span className="text-xs text-muted-foreground tabular-nums">
                {result.text ? `${result.text.trim().split(/\s+/).length} words` : ""}
              </span>
              <div className="ml-auto flex gap-1.5">
                <CopyButton text={result.text} label="Copy letter" />
                <DownloadButton text={result.text} filename={`cover-letter-${jobId.slice(0, 8)}.md`} mime="text/markdown;charset=utf-8" label="Download" />
              </div>
            </div>
            {result.text ? (
              <StreamingText content={result.text} className="rounded-lg border border-border/70 bg-muted/20 p-4" />
            ) : (
              <p className="text-sm text-muted-foreground">
                The response contained no letter text — try regenerating.
              </p>
            )}
            {evidence.length > 0 && <EvidenceList items={evidence} limit={2} dense />}
          </div>
        )}

        {!result && !mutation.isPending && (
          <p className="text-xs text-muted-foreground">No letter generated yet for this role.</p>
        )}
      </CardContent>
    </Card>
  );
}
