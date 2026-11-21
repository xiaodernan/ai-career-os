"use client";

import * as React from "react";
import { Mic } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { useLocale } from "@/lib/i18n/locale-context";
import { formatDate } from "@/lib/format";
import { rehearsalRhythm, type RhythmInput } from "@/lib/rehearsal-rhythm";

/**
 * How long it has been since the reader last rehearsed (Epic 374).
 *
 * The list shows what happened; this says what has NOT happened lately. A rehearsal
 * is a skill and a skill goes stale, so the reader who took four in October and none
 * since is not lazy -- they are out of the habit, and nothing said so.
 *
 * It is a nudge, not a score: no number of "missed" days is ever framed as a
 * failure, and a reader who has never rehearsed gets a different sentence (they have
 * not started) rather than the same one with a bigger number.
 */
const TONE = {
  none: "border-border/60 bg-muted/20",
  fresh: "border-success/25 bg-success/[0.05]",
  warm: "border-border/60 bg-muted/20",
  stale: "border-primary/20 bg-primary/[0.05]",
} as const;

export function RhythmCard({ input }: { input: RhythmInput }) {
  const { t, locale } = useLocale();
  const rhythm = React.useMemo(() => rehearsalRhythm(input), [input]);

  const body =
    rhythm.band === "none"
      ? t("interviews.rhythmNoneBody")
      : rhythm.band === "fresh"
        ? t("interviews.rhythmFreshBody", { days: rhythm.daysSince ?? 0 })
        : rhythm.band === "warm"
          ? t("interviews.rhythmWarmBody", {
              days: rhythm.daysSince ?? 0,
              last: rhythm.lastAt ? formatDate(rhythm.lastAt, locale) : "",
            })
          : t("interviews.rhythmStaleBody", {
              days: rhythm.daysSince ?? 0,
              last: rhythm.lastAt ? formatDate(rhythm.lastAt, locale) : "",
            });

  return (
    <Card data-testid="rhythm-card" className={TONE[rhythm.band]}>
      <CardContent className="flex flex-wrap items-center gap-4 p-5">
        <span className="flex size-10 shrink-0 items-center justify-center rounded-xl border border-primary/25 bg-primary/10 text-primary">
          <Mic aria-hidden className="size-5" />
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-2xs font-semibold uppercase tracking-widest text-primary">
            {t("interviews.rhythmEyebrow")}
          </p>
          <p className="mt-1 text-sm font-medium">
            {rhythm.band === "none"
              ? t("interviews.rhythmNoneTitle")
              : rhythm.band === "fresh"
                ? t("interviews.rhythmFreshTitle", { days: rhythm.daysSince ?? 0 })
                : t("interviews.rhythmStaleTitle", { days: rhythm.daysSince ?? 0 })}
          </p>
          <p className="mt-0.5 text-xs leading-relaxed text-muted-foreground">{body}</p>
        </div>
      </CardContent>
    </Card>
  );
}
