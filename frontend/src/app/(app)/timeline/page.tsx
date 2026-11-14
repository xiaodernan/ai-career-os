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
import { VirtualList } from "@/components/common/virtual-list";
import { useTimeline } from "@/lib/hooks/timeline";
import { useUrlState } from "@/lib/hooks/use-url-state";
import { useLocale } from "@/lib/i18n/locale-context";
import { formatDateTime, formatTime } from "@/lib/format";
import type { TimelineEntry } from "@/lib/api/types";

// Module-level so `setUrl` (a `useCallback` keyed on this object) is stable across renders.
// `kind` is the one narrowing the timeline accepts in the URL, and a `?kind=bogus` narrows
// to the rows with that exact kind (which honestly can be none) rather than to nothing at all.
const PAGE_DEFAULTS: { kind?: string } = { kind: undefined };

/** Constant row geometry: the windowed path requires a row that never wraps. */
const ROW_HEIGHT = 72;
/**
 * Below this, the full render stays and the DOM is simple; past it, the window engages.
 * The engine's own fold caps per source at 50 (`PER_SOURCE_CAP`), so a power-user's
 * timeline converges near 100 rows -- a threshold of 100 would never engage. 30 keeps
 * the window meaningful for realistic folds without disturbing small feeds.
 */
const VIRTUAL_THRESHOLD = 30;

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
const KIND_VISUALS: Record<string, { icon: LucideIcon; labelKey: string; href?: (refId: string) => string; tint: string }> = {
  application: { icon: Briefcase, labelKey: "timeline.kinds.application", href: (id) => `/applications?application=${encodeURIComponent(id)}`, tint: "text-primary border-primary/30 bg-primary/10" },
  note: { icon: StickyNote, labelKey: "timeline.kinds.note", tint: "text-warning border-warning/40 bg-warning/10" },
  contact: { icon: Users, labelKey: "timeline.kinds.contact", tint: "text-success border-success/40 bg-success/10" },
  resume_version: { icon: FileText, labelKey: "timeline.kinds.resume_version", href: (id) => `/resumes/${encodeURIComponent(id)}`, tint: "text-primary border-primary/30 bg-primary/10" },
  match: { icon: Target, labelKey: "timeline.kinds.match", tint: "text-success border-success/40 bg-success/10" },
  interview: { icon: MessageSquare, labelKey: "timeline.kinds.interview", href: (id) => `/interviews/${encodeURIComponent(id)}`, tint: "text-destructive border-destructive/40 bg-destructive/10" },
  unknown: { icon: History, labelKey: "timeline.kinds.unknown", tint: "text-muted-foreground border-border/60 bg-muted" },
};

const RowBody = React.memo(function RowBody({ event, locale, clockOnly = false }: {
  event: TimelineEntry;
  locale: "en" | "zh";
  /** Inside a day group the rail owns the date; the row carries only the clock. */
  clockOnly?: boolean;
}) {
  const { t } = useLocale();
  const visual: (typeof KIND_VISUALS)[string] = KIND_VISUALS[event.kind] ?? KIND_VISUALS.unknown;
  const Icon = visual.icon;
  const href = visual.href?.(event.refId);
  const title = event.title || t("timeline.kinds.unknown");
  const titleNode = href ? (
    <Link href={href} title={title} className="block truncate text-foreground hover:underline underline-offset-4">
      {title}
    </Link>
  ) : (
    <span title={title} className="block truncate font-medium text-foreground">{title}</span>
  );
  return (
    <div className="group flex h-16 items-center gap-3 rounded-lg border hairline bg-card px-4 shadow-soft transition-all duration-150 hover:-translate-y-0.5 hover:border-primary/30 hover:shadow-card">
      <span
        className={`flex size-8 shrink-0 items-center justify-center rounded-lg border transition-transform duration-200 group-hover:scale-110 [&_svg]:size-4 ${visual.tint}`}
        aria-hidden
      >
        <Icon aria-hidden />
      </span>
      <span className="min-w-0 flex-1 space-y-0.5">
        <span className="flex min-w-0 items-center gap-2">
          <span className="min-w-0 flex-1">{titleNode}</span>
          <Badge variant="outline" className="shrink-0 text-2xs">{t(visual.labelKey)}</Badge>
        </span>
        {event.summary ? (
          <span className="block truncate text-sm text-muted-foreground" title={event.summary}>{event.summary}</span>
        ) : null}
      </span>
      <time
        dateTime={event.at}
        className="shrink-0 text-xs tabular-nums text-muted-foreground"
      >
        {clockOnly ? formatTime(event.at, locale) : formatDateTime(event.at, locale)}
      </time>
    </div>
  );
});

const rowKey = (event: TimelineEntry) => `${event.kind}:${event.refId}:${event.at}`;

/** Local calendar day, the key the rail groups by; the engine's order drives adjacency. */
function dayKeyOf(value: string): { key: string; at: Date } {
  const at = new Date(value);
  return { key: `${at.getFullYear()}-${at.getMonth()}-${at.getDate()}`, at };
}

/** One day on the rail (Epic 197): the date in the margin, the events in the column. */
function DayGroup({ dayKey, at, count, children }: {
  dayKey: string;
  at: Date;
  count: number;
  children: React.ReactNode;
}) {
  const { t, locale } = useLocale();
  const isToday = dayKey === dayKeyOf(new Date().toISOString()).key;
  const day = new Intl.DateTimeFormat(locale, { day: "2-digit" }).format(at);
  const weekday = new Intl.DateTimeFormat(locale, { weekday: "short", month: "short", year: "2-digit" }).format(at);
  return (
    <li className="contents">
      <div className="sticky top-20 flex flex-col items-end self-start pt-1 text-right">
        <span
          className={`text-2xl font-semibold leading-none tabular-nums sm:text-3xl ${
            isToday ? "text-primary" : "text-foreground/90"
          }`}
        >
          {day}
        </span>
        <span className="mt-1 max-w-16 text-2xs uppercase leading-tight tracking-wide text-muted-foreground">
          {weekday}
        </span>
        <span className="mt-1 text-2xs tabular-nums text-muted-foreground/70">
          {t("timeline.dayCount", { count })}
        </span>
      </div>
      <ol className="flex flex-col gap-2 border-l hairline py-1 pl-3 sm:pl-4">
        {children}
      </ol>
    </li>
  );
}

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
  // Epic 197: below the window threshold the feed reads as days, not as a flat list —
  // the margin carries the date, the rows carry only the clock.
  const dayGroups = React.useMemo(() => {
    const groups: Array<{ key: string; at: Date; events: TimelineEntry[] }> = [];
    for (const event of visible) {
      const { key, at } = dayKeyOf(event.at);
      const last = groups[groups.length - 1];
      if (last && last.key === key) {
        last.events.push(event);
      } else {
        groups.push({ key, at, events: [event] });
      }
    }
    return groups;
  }, [visible]);

  return (
    <div className="flex flex-col gap-6">
      <PageHeader frontDoor title={t("timeline.title")} description={t("timeline.description")} />
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
          // Epic 141: past the threshold, the window engages -- a reader who opened the
          // timeline to look at one recent event no longer pays to draw ten thousand.
          // Below it, the feed reads as days on a rail (Epic 197); past it, the window
          // keeps constant-height rows.
          if (visible.length > VIRTUAL_THRESHOLD) {
            return (
              <VirtualList
                items={visible}
                rowHeight={ROW_HEIGHT}
                getKey={rowKey}
                renderItem={(event) => <RowBody event={event} locale={locale} />}
                className="h-[70vh] overflow-y-auto"
                aria-label={t("timeline.title")}
              />
            );
          }
          return (
            <ol className="grid grid-cols-[3.5rem_1fr] gap-x-3 gap-y-6 sm:grid-cols-[4.5rem_1fr] sm:gap-x-4">
              {dayGroups.map((group) => (
                <DayGroup
                  key={group.key}
                  dayKey={group.key}
                  at={group.at}
                  count={group.events.length}
                >
                  {group.events.map((event) => (
                    <li key={rowKey(event)}>
                      <RowBody event={event} locale={locale} clockOnly />
                    </li>
                  ))}
                </DayGroup>
              ))}
            </ol>
          );
        }}
      </QueryBoundary>
    </div>
  );
}
