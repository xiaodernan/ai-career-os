"use client";

import * as React from "react";
import { BookOpenText, Sparkles } from "lucide-react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { SectionHeading } from "@/components/common/export-buttons";
import { useCareerNarrative } from "@/lib/hooks/timeline";
import { useLocale } from "@/lib/i18n/locale-context";
import type { TimelineEntry } from "@/lib/api/types";

/**
 * Epic 345 — the timeline's second voice. The ledger is correct but it does not
 * say what the search WAS. This card sends the rows the page already drew to the
 * engine, which writes one paragraph over their own dates and labels — the arc,
 * the turn, the open thread — and stays silent rather than inventing a milestone.
 */
export function CareerNarrativeCard({ events }: { events: TimelineEntry[] }) {
  const { t } = useLocale();
  const narrative = useCareerNarrative();

  const run = React.useCallback(() => {
    narrative.mutate(events);
  }, [narrative, events]);

  // Read from the mutation's own result, not an inline callback (the latter
  // collides with the stream-handler census's shape scan).
  const asked = narrative.isSuccess || narrative.isError;
  const shown = narrative.data?.narrative ?? null;

  return (
    <Card className="border-primary/20 shadow-card">
      <CardHeader className="pb-3">
        <SectionHeading
          eyebrow={t("eyebrows.reviewerAgent")}
          icon={<BookOpenText className="size-4" aria-hidden />}
          title={t("timeline.narrativeTitle")}
          description={t("timeline.narrativeDescription")}
        />
      </CardHeader>
      <CardContent className="space-y-3">
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={run}
          disabled={events.length === 0 || narrative.isPending}
          aria-label={t("timeline.narrativeAction")}
          title={t("timeline.narrativeAction")}
        >
          <Sparkles aria-hidden className="size-4" />
          {narrative.isPending ? t("timeline.narrativeWorking") : t("timeline.narrativeAction")}
        </Button>
        {asked && !narrative.isPending && shown && (
          <p className="text-sm leading-relaxed text-foreground/90">{shown}</p>
        )}
        {asked && !narrative.isPending && !shown && (
          <p className="text-xs leading-relaxed text-muted-foreground">
            {t("timeline.narrativeEmpty")}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
