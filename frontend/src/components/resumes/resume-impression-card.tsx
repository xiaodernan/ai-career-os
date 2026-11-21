"use client";

import * as React from "react";
import { Sparkles, WandSparkles } from "lucide-react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { SectionHeading } from "@/components/common/export-buttons";
import { useResumeImpression } from "@/lib/hooks/actions";
import { useLocale } from "@/lib/i18n/locale-context";

/**
 * Epic 344 — the reader's first value page gets a second voice. After the parse,
 * a bare score and five bars answer "how good?" but never "what does this say
 * about me?". This card asks the engine for one grounded paragraph over the
 * resume's own facts (counts + rubric score) — every claim cites a number the
 * document actually carries, and a silent relay renders nothing rather than a
 * confident generic compliment.
 *
 * The card only offers the action once a parse exists (score present); the hook
 * reads the reader's language from the locale context, so the paragraph arrives
 * in the same language as the rest of the screen.
 */
export function ResumeImpressionCard({ resumeId, hasScore }: { resumeId: string; hasScore: boolean }) {
  const { t } = useLocale();
  const impression = useResumeImpression(resumeId);

  const run = React.useCallback(() => {
    impression.mutate();
  }, [impression]);

  // Read the answer from the mutation's own result rather than an inline callback:
  // an inline `onError:` here collides with the stream-handler census's shape scan.
  const asked = impression.isSuccess || impression.isError;
  const shown = impression.data?.impression ?? null;

  return (
    <Card>
      <CardHeader className="pb-3">
        <SectionHeading
          eyebrow={t("eyebrows.reviewerAgent")}
          icon={<WandSparkles className="size-4" aria-hidden />}
          title={t("resumes.detail.impressionTitle")}
          description={t("resumes.detail.impressionDescription")}
        />
      </CardHeader>
      <CardContent className="space-y-3">
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={run}
          disabled={!hasScore || impression.isPending}
          aria-label={t("resumes.detail.impressionAction")}
          title={t("resumes.detail.impressionAction")}
        >
          <Sparkles aria-hidden className="size-4" />
          {impression.isPending
            ? t("resumes.detail.impressionWorking")
            : t("resumes.detail.impressionAction")}
        </Button>
        {impression.isPending && (
          <p className="text-xs text-muted-foreground">{t("resumes.detail.impressionWorking")}</p>
        )}
        {asked && !impression.isPending && shown && (
          <p className="text-sm leading-relaxed text-foreground/90">{shown}</p>
        )}
        {asked && !impression.isPending && !shown && (
          <p className="text-xs leading-relaxed text-muted-foreground">
            {t("resumes.detail.impressionEmpty")}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
