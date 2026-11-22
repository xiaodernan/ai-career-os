"use client";

import * as React from "react";
import Link from "next/link";
import {
  CalendarDays,
  ChevronLeft,
  ChevronRight,
  Feather,
  Sparkles,
  Users,
  type LucideIcon,
} from "lucide-react";
import { PageHeader } from "@/components/common/page-header";
import { ErrorState } from "@/components/common/error-state";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Hint } from "@/components/ui/hint";
import { useUrlState } from "@/lib/hooks/use-url-state";
import { useLocale } from "@/lib/i18n/locale-context";
import { formatDateOnly } from "@/lib/format";
import { useApplications, useDashboard, useInterviewSessions, useKnowledgeNotes } from "@/lib/hooks/resources";
import { CAPSULE_TAG, localDateKey } from "@/lib/time-capsule";
import {
  buildEvents,
  eventsInMonth,
  monthCells,
  monthKeyOf,
  nextEvent,
  readMonthKey,
  shiftMonth,
  summarize,
  type CalendarEvent,
  type CalendarKind,
} from "@/lib/search-calendar";

const PAGE_DEFAULTS: { month?: string } = { month: undefined };

const KIND_VISUALS: Record<CalendarKind, { icon: LucideIcon; labelKey: string; dot: string; chip: string }> = {
  reminder: {
    icon: CalendarDays,
    labelKey: "monthCalendar.legendReminder",
    dot: "bg-primary",
    chip: "border-primary/30 bg-primary/10 text-primary",
  },
  followup: {
    icon: Users,
    labelKey: "monthCalendar.legendFollowup",
    dot: "bg-success",
    chip: "border-success/40 bg-success/10 text-success",
  },
  interview: {
    icon: Sparkles,
    labelKey: "monthCalendar.legendInterview",
    dot: "bg-warning",
    chip: "border-warning/40 bg-warning/10 text-warning",
  },
  capsule: {
    icon: Feather,
    labelKey: "monthCalendar.legendCapsule",
    dot: "bg-muted-foreground",
    chip: "border-border/70 bg-muted/60 text-muted-foreground",
  },
};

const KIND_ORDER: CalendarKind[] = ["reminder", "followup", "interview", "capsule"];

/** A chip is one fact; past this many the cell says "+N" instead of growing a wall. */
const MAX_CHIPS = 3;

/**
 * Epic 386 — the search on a calendar. The product writes dated rows in seven
 * places, and the reader plans in days: a reminder, a follow-up gone due, a
 * rehearsal and a sealed letter are all "a day". This page lays the rows the
 * other screens already hold on a Monday-first month, with no new endpoint and
 * no model call. A row without a readable date is dropped rather than guessed;
 * a sealed letter contributes its opening day, never its body.
 */
export default function CalendarPage() {
  const { t, locale } = useLocale();
  const [url, setUrl] = useUrlState(PAGE_DEFAULTS);

  const today = localDateKey();
  const month = readMonthKey(url.month) ?? monthKeyOf(new Date(`${today}T00:00:00`));

  const applications = useApplications({ size: 100 });
  const interviews = useInterviewSessions({ size: 100 });
  const dashboard = useDashboard();
  const notes = useKnowledgeNotes({ tag: CAPSULE_TAG, size: 50 });

  const events = React.useMemo(
    () =>
      buildEvents({
        applications: applications.data?.items,
        interviews: interviews.data?.items,
        followUps: dashboard.data?.followUps,
        notes: notes.data?.items,
        today,
      }),
    [applications.data?.items, interviews.data?.items, dashboard.data?.followUps, notes.data?.items, today]
  );

  const monthEvents = React.useMemo(() => eventsInMonth(events, month), [events, month]);
  const counts = React.useMemo(
    () => summarize([...monthEvents.values()].flat()),
    [monthEvents]
  );
  const upcoming = React.useMemo(() => nextEvent(events, today), [events, today]);
  const cells = React.useMemo(() => monthCells(month), [month]);

  const monthLabel = React.useMemo(
    () =>
      new Intl.DateTimeFormat(locale === "zh" ? "zh-CN" : "en-US", {
        month: "long",
        year: "numeric",
      }).format(new Date(`${month}-01T00:00:00`)),
    [month, locale]
  );

  const weekdays = React.useMemo(() => {
    const formatter = new Intl.DateTimeFormat(locale === "zh" ? "zh-CN" : "en-US", { weekday: "short" });
    // 2024-01-01 is a Monday; the grid is Monday-first in every language.
    return Array.from({ length: 7 }, (_, index) => formatter.format(new Date(2024, 0, 1 + index)));
  }, [locale]);

  const pending = applications.isPending || interviews.isPending;
  const failed = applications.isError || interviews.isError;

  const refresh = () => {
    void applications.refetch();
    void interviews.refetch();
    void dashboard.refetch();
    void notes.refetch();
  };

  const go = (delta: number) => setUrl({ month: shiftMonth(month, delta) });

  return (
    <div className="space-y-6">
      <PageHeader
        frontDoor
        title={t("monthCalendar.title")}
        description={t("monthCalendar.description")}
        actions={
          <div className="flex items-center gap-2">
            <Hint side="bottom" label={t("monthCalendar.hintPrev")}>
              <Button
                variant="outline"
                size="icon-sm"
                aria-label={t("monthCalendar.prev")}
                onClick={() => go(-1)}
              >
                <ChevronLeft aria-hidden className="size-4" />
              </Button>
            </Hint>
            <Hint side="bottom" label={t("monthCalendar.hintToday")}>
              <Button variant="outline" size="sm" onClick={() => setUrl({ month: monthKeyOf() })}>
                {t("monthCalendar.today")}
              </Button>
            </Hint>
            <Hint side="bottom" label={t("monthCalendar.hintNext")}>
              <Button
                variant="outline"
                size="icon-sm"
                aria-label={t("monthCalendar.next")}
                onClick={() => go(1)}
              >
                <ChevronRight aria-hidden className="size-4" />
              </Button>
            </Hint>
          </div>
        }
      />

      {failed && (
        <ErrorState
          title={t("monthCalendar.loadFailed")}
          error={applications.error ?? interviews.error}
          onRetry={refresh}
          retrying={applications.isFetching || interviews.isFetching}
        />
      )}

      {!failed && pending && (
        <div className="space-y-3">
          <Skeleton className="h-10 w-56 rounded-lg" />
          <Skeleton className="h-[520px] rounded-xl" />
        </div>
      )}

      {!failed && !pending && (
        <>
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h2 className="font-display text-2xl text-foreground">{monthLabel}</h2>
            <p className="text-sm text-muted-foreground tabular-nums">
              {t("monthCalendar.eventCount", { count: [...monthEvents.values()].flat().length })}
            </p>
          </div>

          <Card className="overflow-hidden">
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <div className="min-w-[720px]">
                  <div className="grid grid-cols-7 border-b border-border/60 bg-muted/30">
                    {weekdays.map((weekday) => (
                      <div
                        key={weekday}
                        className="px-2 py-2 text-center text-2xs font-medium uppercase tracking-wide text-muted-foreground"
                      >
                        {weekday}
                      </div>
                    ))}
                  </div>
                  <div className="grid grid-cols-7">
                    {cells.map((cell) => {
                      const dayEvents = monthEvents.get(cell.date) ?? [];
                      const shown = dayEvents.slice(0, MAX_CHIPS);
                      const hidden = dayEvents.length - shown.length;
                      const isToday = cell.date === today;
                      return (
                        <div
                          key={cell.date}
                          className={[
                            "min-h-24 border-b border-r border-border/50 p-1.5 align-top",
                            cell.inMonth ? "bg-card/40" : "bg-muted/20",
                            isToday ? "ring-1 ring-inset ring-primary/50" : "",
                          ].join(" ")}
                        >
                          <div
                            className={[
                              "mb-1 flex items-center justify-between text-2xs tabular-nums",
                              cell.inMonth ? "text-muted-foreground" : "text-muted-foreground/50",
                            ].join(" ")}
                          >
                            <span
                              className={
                                isToday
                                  ? "inline-flex size-5 items-center justify-center rounded-full bg-primary font-semibold text-primary-foreground"
                                  : ""
                              }
                            >
                              {Number(cell.date.slice(8, 10))}
                            </span>
                          </div>
                          <ul className="space-y-1">
                            {shown.map((event) => (
                              <li key={event.id}>
                                <EventChip event={event} />
                              </li>
                            ))}
                          </ul>
                          {hidden > 0 && (
                            <p className="mt-1 px-1 text-2xs text-muted-foreground tabular-nums">
                              {t("monthCalendar.more", { count: hidden })}
                            </p>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {monthEvents.size === 0 && (
            <p className="text-sm leading-relaxed text-muted-foreground">{t("monthCalendar.monthEmpty")}</p>
          )}

          <div className="grid gap-4 lg:grid-cols-[1fr_1.1fr]">
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base">{t("monthCalendar.legendTitle")}</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="grid grid-cols-2 gap-2">
                  {KIND_ORDER.map((kind) => {
                    const visual = KIND_VISUALS[kind];
                    return (
                      <li key={kind} className="flex items-center gap-2 text-sm text-muted-foreground">
                        <span aria-hidden className={`size-2 rounded-full ${visual.dot}`} />
                        <span className="min-w-0 truncate">{t(visual.labelKey)}</span>
                        <span className="ml-auto font-mono text-xs tabular-nums text-foreground">
                          {counts[kind]}
                        </span>
                      </li>
                    );
                  })}
                </ul>
                <p className="mt-3 text-2xs leading-relaxed text-muted-foreground">
                  {t("monthCalendar.legendHint")}
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base">{t("monthCalendar.nextTitle")}</CardTitle>
              </CardHeader>
              <CardContent>
                {upcoming ? (
                  <div className="flex items-start gap-3">
                    <span
                      aria-hidden
                      className={`mt-1.5 size-2 shrink-0 rounded-full ${KIND_VISUALS[upcoming.kind].dot}`}
                    />
                    <div className="min-w-0">
                      <p className="text-sm leading-relaxed text-foreground">
                        {upcoming.title || t("monthCalendar.capsuleEvent")}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {formatDateOnly(upcoming.date, locale)} · {t(KIND_VISUALS[upcoming.kind].labelKey)}
                      </p>
                      {upcoming.href && (
                        <Link
                          href={upcoming.href}
                          className="mt-1 inline-block text-xs font-medium text-primary underline-offset-4 hover:underline"
                        >
                          {t("monthCalendar.open")}
                        </Link>
                      )}
                    </div>
                  </div>
                ) : (
                  <p className="text-sm leading-relaxed text-muted-foreground">{t("monthCalendar.noUpcoming")}</p>
                )}
              </CardContent>
            </Card>
          </div>
        </>
      )}

      {!failed && !pending && events.length === 0 && (
        <Card className="border-dashed">
          <CardContent className="space-y-3 p-6">
            <p className="font-medium text-foreground">{t("monthCalendar.emptyTitle")}</p>
            <p className="max-w-2xl text-sm leading-relaxed text-muted-foreground">{t("monthCalendar.emptyBody")}</p>
            <div className="flex flex-wrap gap-2">
              <Button asChild variant="outline" size="sm">
                <Link href="/applications">{t("monthCalendar.emptyApplications")}</Link>
              </Button>
              <Button asChild variant="outline" size="sm">
                <Link href="/timeline">{t("monthCalendar.emptyTimeline")}</Link>
              </Button>
              <Button asChild variant="outline" size="sm">
                <Link href="/networking">{t("monthCalendar.emptyNetworking")}</Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function EventChip({ event }: { event: CalendarEvent }) {
  const { t } = useLocale();
  const visual = KIND_VISUALS[event.kind];
  const Icon = visual.icon;
  const label = event.title || t("monthCalendar.capsuleEvent");
  const title = `${t(visual.labelKey)} · ${label}`;
  const body = (
    <span
      title={title}
      className={`flex items-center gap-1 rounded border px-1.5 py-0.5 text-2xs leading-tight ${visual.chip}`}
    >
      <Icon aria-hidden className="size-3 shrink-0" />
      <span className="min-w-0 truncate">{label}</span>
    </span>
  );
  return event.href ? (
    <Link href={event.href} className="block focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40">
      {body}
    </Link>
  ) : (
    body
  );
}
