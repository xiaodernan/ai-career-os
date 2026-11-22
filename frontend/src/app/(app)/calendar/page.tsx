"use client";

import * as React from "react";
import Link from "next/link";
import {
  CalendarDays,
  ChevronLeft,
  ChevronRight,
  Download,
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
import { CAPSULE_TAG, daysUntil, localDateKey } from "@/lib/time-capsule";
import { buildCalendarIcs } from "@/lib/calendar-ics";
import {
  buildEvents,
  eventsInMonth,
  eventsInWeek,
  monthCells,
  monthKeyOf,
  readCalendarView,
  readDayKey,
  readMonthKey,
  shiftDays,
  shiftMonth,
  summarize,
  upcomingEvents,
  weekCells,
  type CalendarEvent,
  type CalendarKind,
  type CalendarView,
} from "@/lib/search-calendar";

const PAGE_DEFAULTS: { month?: string; view?: string; day?: string } = {
  month: undefined,
  view: undefined,
  day: undefined,
};

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
  const view: CalendarView = readCalendarView(url.view);
  const weekAnchor = readDayKey(url.day) ?? today;
  const week = React.useMemo(() => weekCells(weekAnchor), [weekAnchor]);
  const weekEvents = React.useMemo(() => eventsInWeek(events, weekAnchor), [events, weekAnchor]);
  const shownEvents = view === "week" ? weekEvents : monthEvents;
  const counts = React.useMemo(
    () => summarize([...shownEvents.values()].flat()),
    [shownEvents]
  );
  const upcoming = React.useMemo(() => upcomingEvents(events, today, 5), [events, today]);
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

  const weekLabel = React.useMemo(() => {
    const first = new Date(`${week[0].date}T00:00:00`);
    const last = new Date(`${week[6].date}T00:00:00`);
    const formatter = new Intl.DateTimeFormat(locale === "zh" ? "zh-CN" : "en-US", {
      month: "short",
      day: "numeric",
    });
    if (locale === "zh") {
      return `${last.getFullYear()}年${formatter.format(first)} – ${formatter.format(last)}`;
    }
    return `${formatter.format(first)} – ${formatter.format(last)}, ${last.getFullYear()}`;
  }, [week, locale]);

  const pending = applications.isPending || interviews.isPending;
  const failed = applications.isError || interviews.isError;

  const refresh = () => {
    void applications.refetch();
    void interviews.refetch();
    void dashboard.refetch();
    void notes.refetch();
  };

  const go = (delta: number) => {
    if (view === "week") {
      setUrl({ day: shiftDays(weekAnchor, delta * 7) });
      return;
    }
    setUrl({ month: shiftMonth(month, delta) });
  };

  const goToday = () => {
    if (view === "week") {
      setUrl({ day: today, month: undefined });
      return;
    }
    setUrl({ month: monthKeyOf(), day: undefined });
  };

  const switchView = (next: CalendarView) => {
    if (next === view) return;
    if (next === "week") {
      setUrl({ view: "week", day: weekAnchor });
      return;
    }
    // Walking back to the month keeps the week the reader was looking at.
    setUrl({ view: undefined, day: undefined, month: weekAnchor.slice(0, 7) });
  };

  // Epic 391 — the grid the reader is looking at, as a file any calendar reads.
  // It is the same arithmetic the page already did; nothing is re-read, invented
  // or sent anywhere.
  const exportCalendar = () => {
    const rows = [...shownEvents.values()].flat();
    if (rows.length === 0) return;
    const ics = buildCalendarIcs(rows, {
      calendarName: `${t("monthCalendar.icsCalendarName")} · ${view === "week" ? weekLabel : monthLabel}`,
      kindLabels: {
        reminder: t("monthCalendar.legendReminder"),
        followup: t("monthCalendar.legendFollowup"),
        interview: t("monthCalendar.legendInterview"),
        capsule: t("monthCalendar.legendCapsule"),
      },
    });
    const blob = new Blob([ics], { type: "text/calendar;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `career-os-${view === "week" ? week[0].date : month}.ics`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 0);
  };

  return (
    <div className="space-y-6">
      <PageHeader
        frontDoor
        title={t("monthCalendar.title")}
        description={t("monthCalendar.description")}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <div
              role="group"
              aria-label={t("monthCalendar.viewLabel")}
              className="flex items-center gap-0.5 rounded-lg border border-border/70 bg-muted/40 p-0.5"
            >
              <Hint side="bottom" label={t("monthCalendar.hintViewMonth")}>
                <Button
                  variant={view === "month" ? "secondary" : "ghost"}
                  size="sm"
                  aria-pressed={view === "month"}
                  onClick={() => switchView("month")}
                >
                  {t("monthCalendar.viewMonth")}
                </Button>
              </Hint>
              <Hint side="bottom" label={t("monthCalendar.hintViewWeek")}>
                <Button
                  variant={view === "week" ? "secondary" : "ghost"}
                  size="sm"
                  aria-pressed={view === "week"}
                  onClick={() => switchView("week")}
                >
                  {t("monthCalendar.viewWeek")}
                </Button>
              </Hint>
            </div>
            <Hint side="bottom" label={t(view === "week" ? "monthCalendar.hintPrevWeek" : "monthCalendar.hintPrev")}>
              <Button
                variant="outline"
                size="icon-sm"
                aria-label={t(view === "week" ? "monthCalendar.prevWeek" : "monthCalendar.prev")}
                onClick={() => go(-1)}
              >
                <ChevronLeft aria-hidden className="size-4" />
              </Button>
            </Hint>
            <Hint side="bottom" label={t("monthCalendar.hintToday")}>
              <Button variant="outline" size="sm" onClick={goToday}>
                {t("monthCalendar.today")}
              </Button>
            </Hint>
            <Hint side="bottom" label={t(view === "week" ? "monthCalendar.hintNextWeek" : "monthCalendar.hintNext")}>
              <Button
                variant="outline"
                size="icon-sm"
                aria-label={t(view === "week" ? "monthCalendar.nextWeek" : "monthCalendar.next")}
                onClick={() => go(1)}
              >
                <ChevronRight aria-hidden className="size-4" />
              </Button>
            </Hint>
            <Hint side="bottom" label={t("monthCalendar.exportHint")}>
              <Button
                variant="outline"
                size="sm"
                disabled={[...shownEvents.values()].flat().length === 0}
                onClick={exportCalendar}
              >
                <Download aria-hidden className="size-4" />
                {t("monthCalendar.export")}
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
            <h2 className="font-display text-2xl text-foreground">{view === "week" ? weekLabel : monthLabel}</h2>
            <p className="text-sm text-muted-foreground tabular-nums">
              {t(view === "week" ? "monthCalendar.weekEventCount" : "monthCalendar.eventCount", {
                count: [...shownEvents.values()].flat().length,
              })}
            </p>
          </div>

          {view === "week" ? (
            <WeekGrid cells={week} events={weekEvents} weekdays={weekdays} today={today} />
          ) : (
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
                            <button
                              type="button"
                              title={t("monthCalendar.moreHint")}
                              onClick={() => setUrl({ view: "week", day: cell.date })}
                              className="mt-1 block w-full rounded px-1 text-left text-2xs text-muted-foreground underline-offset-2 transition-colors hover:text-foreground hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
                            >
                              {t("monthCalendar.more", { count: hidden })}
                            </button>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
          )}

          {view === "week"
            ? weekEvents.size === 0 && (
                <p className="text-sm leading-relaxed text-muted-foreground">{t("monthCalendar.weekEmpty")}</p>
              )
            : monthEvents.size === 0 && (
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
                {upcoming.length > 0 ? (
                  <ol className="space-y-3">
                    {upcoming.map((event) => {
                      const days = daysUntil(event.date, today);
                      const when =
                        days === 0
                          ? t("monthCalendar.nextToday")
                          : days === 1
                            ? t("monthCalendar.nextTomorrow")
                            : t("monthCalendar.nextInDays", { days });
                      return (
                        <li key={event.id} className="flex items-start gap-3">
                          <span
                            aria-hidden
                            className={`mt-1.5 size-2 shrink-0 rounded-full ${KIND_VISUALS[event.kind].dot}`}
                          />
                          <div className="min-w-0">
                            <p className="text-sm leading-relaxed text-foreground">
                              {event.title || t("monthCalendar.capsuleEvent")}
                            </p>
                            <p className="text-xs text-muted-foreground">
                              {formatDateOnly(event.date, locale)} · {t(KIND_VISUALS[event.kind].labelKey)} · {when}
                            </p>
                            {event.href && (
                              <Link
                                href={event.href}
                                className="mt-1 inline-block text-xs font-medium text-primary underline-offset-4 hover:underline"
                              >
                                {t("monthCalendar.open")}
                              </Link>
                            )}
                          </div>
                        </li>
                      );
                    })}
                  </ol>
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

/**
 * Epic 388 — the week. The month chip trims a day's rows to three; the week has
 * room for the whole day, so this grid never hides a row behind a counter and
 * prints each row's own detail (a company, a relation) beside its title.
 */
function WeekGrid({
  cells,
  events,
  weekdays,
  today,
}: {
  cells: { date: string; inMonth: boolean }[];
  events: Map<string, CalendarEvent[]>;
  weekdays: string[];
  today: string;
}) {
  const { t, locale } = useLocale();
  const dayFormatter = React.useMemo(
    () =>
      new Intl.DateTimeFormat(locale === "zh" ? "zh-CN" : "en-US", {
        month: "short",
        day: "numeric",
      }),
    [locale]
  );

  return (
    <Card className="overflow-hidden">
      <CardContent className="p-0">
        <div className="overflow-x-auto">
          <div className="grid min-w-[900px] grid-cols-7">
            {cells.map((cell, index) => {
              const dayEvents = events.get(cell.date) ?? [];
              const isToday = cell.date === today;
              return (
                <div
                  key={cell.date}
                  className={[
                    "min-h-[24rem] border-r border-border/50 last:border-r-0",
                    cell.inMonth ? "bg-card/40" : "bg-muted/20",
                    isToday ? "ring-1 ring-inset ring-primary/50" : "",
                  ].join(" ")}
                >
                  <div
                    className={[
                      "border-b border-border/60 px-2 py-2",
                      isToday ? "bg-primary/10" : "bg-muted/30",
                    ].join(" ")}
                  >
                    <p className="text-2xs font-medium uppercase tracking-wide text-muted-foreground">
                      {weekdays[index]}
                    </p>
                    <p
                      className={[
                        "mt-0.5 text-xs tabular-nums",
                        isToday ? "font-semibold text-primary" : "text-foreground",
                      ].join(" ")}
                    >
                      {dayFormatter.format(new Date(`${cell.date}T00:00:00`))}
                    </p>
                  </div>
                  {dayEvents.length > 0 ? (
                    <ul className="space-y-1.5 p-1.5">
                      {dayEvents.map((event) => (
                        <li key={event.id}>
                          <WeekEventRow event={event} />
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="px-2 py-6 text-center text-2xs text-muted-foreground/60">
                      {t("monthCalendar.weekDayEmpty")}
                    </p>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function WeekEventRow({ event }: { event: CalendarEvent }) {
  const { t } = useLocale();
  const visual = KIND_VISUALS[event.kind];
  const Icon = visual.icon;
  const label = event.title || t("monthCalendar.capsuleEvent");
  const title = `${t(visual.labelKey)} · ${label}`;
  const body = (
    <span
      title={title}
      className={`block rounded border px-1.5 py-1 text-2xs leading-snug ${visual.chip}`}
    >
      <span className="flex items-start gap-1">
        <Icon aria-hidden className="mt-0.5 size-3 shrink-0" />
        <span className="min-w-0 break-words font-medium">{label}</span>
      </span>
      {event.detail && (
        <span className="mt-0.5 block break-words pl-4 opacity-75">{event.detail}</span>
      )}
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
