"use client";

import * as React from "react";
import Link from "next/link";
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
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useTimeline } from "@/lib/hooks/timeline";
import { useUrlState } from "@/lib/hooks/use-url-state";
import { useLocale } from "@/lib/i18n/locale-context";
import { formatDateTime } from "@/lib/format";
import type { TimelineEntry } from "@/lib/api/types";

// Module-level so `setUrl` (a `useCallback` keyed on this object) is stable across renders.
// `kind` is the one narrowing the timeline accepts in the URL, and a `?kind=bogus` narrows
// to the rows with that exact kind (which honestly can be none) rather than to nothing at all.
const PAGE_DEFAULTS: { kind?: string } = { kind: undefined };

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
/**
 * Each row is also a door into the screen that owns the fact it names. A link is offered only
 * where the refId actually names a route the browser already serves — `/applications?application=`
 * (deep-link the card), `/resumes/{id}`, `/interviews/{id}` — never a made-up address: the
 * reader stays in control of where the board goes, and the screen's own guard decides whether
 * the id belongs to them.
 */
const KIND_VISUALS: Record<string, { icon: LucideIcon; labelKey: string; href?: (refId: string) => string }> = {
  application: { icon: Briefcase, labelKey: "timeline.kinds.application", href: (id) => `/applications?application=${encodeURIComponent(id)}` },
  note: { icon: StickyNote, labelKey: "timeline.kinds.note" },
  contact: { icon: Users, labelKey: "timeline.kinds.contact" },
  resume_version: { icon: FileText, labelKey: "timeline.kinds.resume_version", href: (id) => `/resumes/${encodeURIComponent(id)}` },
  match: { icon: Target, labelKey: "timeline.kinds.match" },
  interview: { icon: MessageSquare, labelKey: "timeline.kinds.interview", href: (id) => `/interviews/${encodeURIComponent(id)}` },
  unknown: { icon: History, labelKey: "timeline.kinds.unknown" },
};

const TimelineRow = React.memo(function TimelineRow({ event, locale }: {
  event: TimelineEntry;
  locale: "en" | "zh";
}) {
  const { t } = useLocale();
  const visual: { icon: LucideIcon; labelKey: string; href?: (refId: string) => string } =
    KIND_VISUALS[event.kind] ?? KIND_VISUALS.unknown;
  const Icon = visual.icon;
  const href = visual.href?.(event.refId);
  const titleNode = href ? (
    <Link href={href} className="text-foreground hover:underline underline-offset-4">
      {event.title || t("timeline.kinds.unknown")}
    </Link>
  ) : (
    <span className="font-medium text-foreground">{event.title || t("timeline.kinds.unknown")}</span>
  );
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
          <span className="font-medium text-foreground">{titleNode}</span>
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
})

export default function TimelinePage() {
  const { t, locale } = useLocale();
  const query = useTimeline();
  const [state, setUrl] = useUrlState<{ kind?: string }>(PAGE_DEFAULTS);
  const narrowed = (state.kind ?? "").trim();
  const narrowedKind = narrowed.length > 0 ? narrowed : undefined;
  const counts = React.useMemo(() => {
    const out = new Map<string, number>();
    for (const event of query.data ?? []) {
      out.set(event.kind, (out.get(event.kind) ?? 0) + 1);
    }
    return out;
  }, [query.data]);
  // Only the kinds the engine can emit carry a chip — counted rows are the honest
  // answer, and a zero-count kind is not offered (nothing behind it to see).
  const offeredKinds = React.useMemo(
    () => [...counts.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0])),
    [counts]
  );
  const visible = React.useMemo(
    () => (narrowedKind ? (query.data ?? []).filter((event) => event.kind === narrowedKind)
                        : (query.data ?? [])),
    [query.data, narrowedKind]
  );

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title={t("timeline.title")} description={t("timeline.description")} />
      {(offeredKinds.length > 0) ? (
        <section
          className="flex flex-wrap items-center gap-1.5"
          role="group"
          aria-label={t("timeline.kindFilter")}
        >
          <Button
            type="button"
            size="sm"
            variant={narrowedKind ? "ghost" : "secondary"}
            onClick={() => setUrl({ kind: undefined })}
          >
            {t("timeline.filterAll")}
          </Button>
          {offeredKinds.map(([kind, count]) => (
            <Button
              key={kind}
              type="button"
              size="sm"
              variant={narrowedKind === kind ? "secondary" : "ghost"}
              onClick={() => setUrl({ kind: narrowedKind === kind ? undefined : kind })}
              aria-pressed={narrowedKind === kind}
            >
              {t(KIND_VISUALS[kind]?.labelKey ?? KIND_VISUALS.unknown.labelKey)}
              <span className="ml-1 tabular-nums text-muted-foreground">{count}</span>
            </Button>
          ))}
        </section>
      ) : null}
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
        empty={narrowedKind
          ? {
              icon: <History aria-hidden />,
              title: t("timeline.noKindRows", { kind: state.kind ?? "" }),
              description: undefined,
            }
          : {
              icon: <History aria-hidden />,
              title: t("timeline.emptyTitle"),
              description: t("timeline.emptyDescription"),
            }}
      >
        {() => {
          if (visible.length === 0) {
            return (
              <p className="rounded-lg border border-border/60 bg-card px-4 py-6 text-center text-sm text-muted-foreground">
                {t("timeline.noKindRows", { kind: t(KIND_VISUALS[narrowedKind ?? ""]?.labelKey ?? KIND_VISUALS.unknown.labelKey) })}
              </p>
            );
          }
          return (
            <ol className="flex flex-col gap-2">
              {visible.map((event) => (
                <TimelineRow
                  key={`${event.kind}:${event.refId}:${event.at}`}
                  event={event}
                  locale={locale}
                />
              ))}
            </ol>
          );
        }}
      </QueryBoundary>
    </div>
  );
}
