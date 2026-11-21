"use client";

import * as React from "react";
import { BookMarked, ChevronRight, LockKeyhole, Sparkles } from "lucide-react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { SectionHeading } from "@/components/common/export-buttons";
import { useCareerChronicle } from "@/lib/hooks/timeline";
import { useLocale } from "@/lib/i18n/locale-context";
import type { ChronicleChapter, Milestones, TimelineEntry } from "@/lib/api/types";

/**
 * Epic 354 — the Career Chronicle: a short, grounded book about THIS reader's own
 * search. Chapters unlock as their milestone/events warrant; each carries a prose act
 * and concrete lore entries, all anchored to numbers the engine actually saw. The
 * milestone shelf shows badges — this is the meaning those badges stand for.
 *
 * A silent relay answers an empty book, rendered as honest quiet — never an invented
 * epic. Copy is locale-keyed; the prose itself comes from the engine in the reader's
 * language.
 */
export function CareerChronicleCard({
  events,
  milestones,
}: {
  events: TimelineEntry[];
  milestones: Milestones | null | undefined;
}) {
  const { t } = useLocale();
  const chronicle = useCareerChronicle();
  const [openChapter, setOpenChapter] = React.useState<number | null>(0);

  const run = React.useCallback(() => {
    chronicle.mutate({
      events,
      milestones: (milestones?.counters ?? {}) as Record<string, unknown>,
    });
  }, [chronicle, events, milestones]);

  const asked = chronicle.isSuccess || chronicle.isError;
  const chapters: ChronicleChapter[] = chronicle.data?.chapters ?? [];
  const epilogue = chronicle.data?.epilogue ?? "";
  const empty = chronicle.data?.empty ?? false;

  return (
    <Card className="border-primary/20 shadow-card">
      <CardHeader className="pb-3">
        <SectionHeading
          eyebrow={t("eyebrows.reviewerAgent")}
          icon={<BookMarked className="size-4" aria-hidden />}
          title={t("timeline.chronicleTitle")}
          description={t("timeline.chronicleDescription")}
        />
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center justify-between gap-3">
          <p className="text-xs text-muted-foreground">{t("timeline.chronicleLede")}</p>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={run}
            disabled={events.length === 0 || chronicle.isPending}
            aria-label={t("timeline.chronicleAction")}
            title={t("timeline.chronicleAction")}
          >
            <Sparkles aria-hidden className="size-4" />
            {chronicle.isPending ? t("timeline.chronicleWorking") : t("timeline.chronicleAction")}
          </Button>
        </div>

        {asked && !chronicle.isPending && empty && (
          <p className="rounded-xl border border-border/60 bg-muted/30 p-4 text-xs leading-relaxed text-muted-foreground">
            {t("timeline.chronicleEmpty")}
          </p>
        )}

        {asked && !chronicle.isPending && chapters.length > 0 && (
          <ol className="space-y-2">
            {chapters.map((ch, i) => {
              const expanded = openChapter === i;
              return (
                <li key={ch.key} className="overflow-hidden rounded-xl border border-border/60 bg-card">
                  <button
                    type="button"
                    className="flex w-full items-center justify-between gap-3 p-3 text-start transition-colors hover:bg-accent/40 focus-visible:ring-[3px] focus-visible:ring-primary/30"
                    onClick={() => setOpenChapter(expanded ? null : i)}
                    aria-expanded={expanded}
                  >
                    <span className="flex min-w-0 items-center gap-2">
                      <span className="flex size-6 shrink-0 items-center justify-center rounded-md bg-primary/10 text-2xs font-semibold tabular-nums text-primary">
                        {i + 1}
                      </span>
                      <span className="truncate text-sm font-medium">{ch.title || t("timeline.chronicleUntitled")}</span>
                      {ch.anchor && <Badge variant="secondary" className="shrink-0 text-2xs">{ch.anchor}</Badge>}
                    </span>
                    <ChevronRight aria-hidden className={`size-4 shrink-0 text-muted-foreground transition-transform ${expanded ? "rotate-90" : ""}`} />
                  </button>
                  {expanded && (
                    <div className="space-y-3 border-t border-border/60 p-4">
                      <p className="text-sm leading-relaxed text-foreground/90">{ch.prose}</p>
                      {ch.loreEntries && ch.loreEntries.length > 0 && (
                        <ul className="space-y-1.5">
                          {ch.loreEntries.map((line, j) => (
                            <li key={j} className="flex gap-2 text-xs leading-relaxed text-muted-foreground">
                              <BookMarked aria-hidden className="mt-0.5 size-3.5 shrink-0 text-primary" />
                              <span>{line}</span>
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  )}
                </li>
              );
            })}
          </ol>
        )}

        {asked && !chronicle.isPending && epilogue && (
          <div className="rounded-xl border border-primary/20 bg-primary/[0.04] p-4">
            <p className="mb-1 text-2xs font-semibold uppercase tracking-widest text-muted-foreground">
              {t("timeline.chronicleEpilogue")}
            </p>
            <p className="text-sm leading-relaxed text-foreground/90">{epilogue}</p>
          </div>
        )}

        {!asked && (
          <p className="flex items-center gap-2 text-xs text-muted-foreground">
            <LockKeyhole aria-hidden className="size-3.5" />
            {t("timeline.chronicleLocked")}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
