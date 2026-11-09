"use client";

import * as React from "react";
import {
  Briefcase,
  FileText,
  History,
  MessageSquare,
  StickyNote,
  Target,
  Users,
  type LucideIcon,
} from "lucide-react";
import { PageHeader } from "@/components/common/page-header";
import { QueryBoundary } from "@/components/common/query-boundary";
import { Badge } from "@/components/ui/badge";
import { useTimeline } from "@/lib/hooks/timeline";
import { useLocale } from "@/lib/i18n/locale-context";
import { formatDateTime } from "@/lib/format";
import type { TimelineEntry } from "@/lib/api/types";

/**
 * The timeline (Epic 81): one ordered read over what the loop has written
 * down. The merge is not this page's to do — the backend reads the caller's
 * own tables and the ai-service folds them deterministically; this page only
 * hands each event to the row that renders it.
 *
 * The kinds are the engine's own vocabulary (`application`, `note`, `contact`,
 * `resume_version`, `match`, `interview`); anything else arrives as `unknown`
 * and is shown as a generic row rather than hidden — a fact the screens did
 * not know how to host is still a fact.
 */
const KIND_VISUALS: Record<string, { icon: LucideIcon; labelKey: string }> = {
  application: { icon: Briefcase, labelKey: "timeline.kinds.application" },
  note: { icon: StickyNote, labelKey: "timeline.kinds.note" },
  contact: { icon: Users, labelKey: "timeline.kinds.contact" },
  resume_version: { icon: FileText, labelKey: "timeline.kinds.resume_version" },
  match: { icon: Target, labelKey: "timeline.kinds.match" },
  interview: { icon: MessageSquare, labelKey: "timeline.kinds.interview" },
  unknown: { icon: History, labelKey: "timeline.kinds.unknown" },
};

function TimelineRow({ event, locale }: {
  event: TimelineEntry;
  locale: "en" | "zh";
}) {
  const { t } = useLocale();
  const visual: { icon: LucideIcon; labelKey: string } =
    KIND_VISUALS[event.kind] ?? KIND_VISUALS.unknown;
  const Icon = visual.icon;
  return (
    <li className="flex items-start gap-3 rounded-lg border border-border/60 bg-card px-4 py-3 shadow-soft">
      <span
        className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-lg border border-border/70 bg-muted text-muted-foreground [&_svg]:size-4"
        aria-hidden
      >
        <Icon aria-hidden />
      </span>
      <span className="min-w-0 flex-1 space-y-0.5">
        <span className="flex flex-wrap items-center gap-2">
          <span className="font-medium text-foreground">{event.title || t("timeline.kinds.unknown")}</span>
          <Badge variant="outline" className="text-2xs">{t(visual.labelKey)}</Badge>
        </span>
        {event.summary ? (
          <span className="block text-sm text-muted-foreground">{event.summary}</span>
        ) : null}
      </span>
      <time
        dateTime={event.at}
        className="shrink-0 text-xs tabular-nums text-muted-foreground"
      >
        {formatDateTime(event.at, locale)}
      </time>
    </li>
  );
}

export default function TimelinePage() {
  const { t, locale } = useLocale();
  const query = useTimeline();

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title={t("timeline.title")} description={t("timeline.description")} />
      <QueryBoundary
        query={query}
        boxed={false}
        skeleton={
          <ol className="flex flex-col gap-2" aria-hidden>
            {Array.from({ length: 6 }, (_, i) => (
              <li
                key={i}
                className="h-16 animate-pulse rounded-lg border border-border/60 bg-muted/40"
              />
            ))}
          </ol>
        }
        empty={{
          icon: <History aria-hidden />,
          title: t("timeline.emptyTitle"),
          description: t("timeline.emptyDescription"),
        }}
      >
        {(events) => (
          <ol className="flex flex-col gap-2">
            {events.map((event) => (
              <TimelineRow
                key={`${event.kind}:${event.refId}:${event.at}`}
                event={event}
                locale={locale}
              />
            ))}
          </ol>
        )}
      </QueryBoundary>
    </div>
  );
}
