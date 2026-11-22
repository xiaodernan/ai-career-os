"use client";

import * as React from "react";
import { BookOpenText, Cpu } from "lucide-react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { CopyButton, DownloadButton, SectionHeading } from "@/components/common/export-buttons";
import { useLocale } from "@/lib/i18n/locale-context";
import { formatDate } from "@/lib/format";
import { buildLocalChronicle, type ChronicleVar } from "@/lib/local-chronicle";
import type { TimelineEntry } from "@/lib/api/types";

/**
 * Epic 380 — the chronicle's local pen. The model-written chronicle is a second
 * voice that needs a live provider; this card is the floor under it. It composes
 * the reader's own book from the rows the timeline already drew, in either
 * language, with zero model calls, so a closed account cannot leave the page
 * without a story.
 */
export function LocalChronicleCard({ events }: { events: TimelineEntry[] }) {
  const { t, locale } = useLocale();
  const book = React.useMemo(() => buildLocalChronicle(events), [events]);

  const withDates = React.useCallback(
    (vars: ChronicleVar): ChronicleVar =>
      Object.fromEntries(
        Object.entries(vars).map(([key, value]) => [
          key,
          (key === "first" || key === "last") && typeof value === "string"
            ? formatDate(value, locale)
            : value,
        ]),
      ),
    [locale],
  );

  if (book.empty) return null;

  const markdown = [
    `# ${t("timeline.localTitle")}`,
    "",
    t("timeline.localDescription"),
    "",
    ...book.chapters.flatMap((chapter) => [
      `## ${t(chapter.titleKey, withDates(chapter.titleVars))}`,
      "",
      t(chapter.bodyKey, withDates(chapter.bodyVars)),
      "",
      ...chapter.lore.map((line) => `- ${t(line.key, line.vars)}`),
      ...(chapter.lore.length > 0 ? [""] : []),
    ]),
    "---",
    "",
    t(book.epilogueKey, withDates(book.epilogueVars)),
  ].join("\n");

  return (
    <Card className="border-border/70 shadow-card">
      <CardHeader className="pb-3">
        <SectionHeading
          eyebrow={t("eyebrows.localChronicler")}
          icon={<BookOpenText className="size-4" aria-hidden />}
          title={t("timeline.localTitle")}
          description={t("timeline.localDescription")}
        />
      </CardHeader>
      <CardContent className="space-y-4">
        <Badge variant="secondary" className="gap-1.5 text-2xs">
          <Cpu aria-hidden className="size-3" />
          {t("timeline.localBadge")}
        </Badge>

        <div className="flex flex-wrap gap-2">
          <CopyButton text={markdown} label={t("timeline.localCopy")} size="xs" />
          <DownloadButton
            text={markdown}
            filename="career-chronicle.md"
            label={t("timeline.localDownload")}
            size="xs"
          />
        </div>

        <ol className="space-y-3">
          {book.chapters.map((chapter, index) => (
            <li key={chapter.id} className="rounded-xl border border-border/60 bg-card/60 p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h3 className="min-w-0 text-sm font-semibold">
                  <span className="mr-2 tabular-nums text-2xs text-primary">
                    {String(index + 1).padStart(2, "0")}
                  </span>
                  {t(chapter.titleKey, withDates(chapter.titleVars))}
                </h3>
                {chapter.regions.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {chapter.regions.map((region) => (
                      <Badge key={region} variant="outline" className="text-2xs">
                        {t(`timeline.kinds.${region}`)}
                      </Badge>
                    ))}
                  </div>
                )}
              </div>
              <p className="mt-1.5 text-sm leading-relaxed text-foreground/90">
                {t(chapter.bodyKey, withDates(chapter.bodyVars))}
              </p>
              {chapter.lore.length > 0 && (
                <ul className="mt-2 space-y-1">
                  {chapter.lore.map((line, lineIndex) => (
                    <li key={`${chapter.id}-${lineIndex}-${line.vars.title}`} className="flex gap-2 text-xs leading-relaxed text-muted-foreground">
                      <BookOpenText aria-hidden className="mt-0.5 size-3 shrink-0 text-primary" />
                      <span className="min-w-0 break-words">{t(line.key, line.vars)}</span>
                    </li>
                  ))}
                </ul>
              )}
            </li>
          ))}
        </ol>

        {book.frontier.length > 0 && (
          <div className="rounded-xl border border-dashed border-border/70 p-3">
            <p className="text-2xs uppercase tracking-widest text-muted-foreground">
              {t("timeline.localFrontierTitle")}
            </p>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {book.frontier.map((region) => (
                <Badge key={region} variant="secondary" className="text-2xs">
                  {t(`timeline.kinds.${region}`)}
                </Badge>
              ))}
            </div>
          </div>
        )}

        <p className="border-t border-border/60 pt-3 text-xs italic leading-relaxed text-muted-foreground">
          {t(book.epilogueKey, withDates(book.epilogueVars))}
        </p>
      </CardContent>
    </Card>
  );
}
