"use client";

import * as React from "react";
import { Flame } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useActivityHeatmap } from "@/lib/hooks/monitoring";
import { useLocale } from "@/lib/i18n/locale-context";
import type { ActivityHeatmapDay } from "@/lib/api/types";
import { cn } from "@/lib/utils";

/**
 * The reader's pace as one dense day-grid (Epic 184) — the GitHub-shaped answer to
 * "how is my search actually going", drawn from the four tables the backend already
 * owns: applications filed, interviews held, replies received, AI calls made.
 *
 * The shape rules: weeks are columns, weekdays are rows, Monday first (the reading
 * convention both locales here share); a month label sits over the column that
 * first touches it; intensity is the day's total, bucketed to five steps so the
 * ramp reads at a glance. Quiet days are IN the grid — a week of silence between
 * two busy ones must read as silence, not as a shorter calendar. The streak chips
 * carry the two numbers the grid exists for: the chain the reader is on (which
 * forgives an in-progress today) and the best chain the window remembers.
 */

const WEEKDAYS = 7;
/** Intensity buckets: [min-total, class] — five steps, from quiet to on-fire. */
const RAMP: Array<[number, string]> = [
  [1, "bg-success/20"],
  [3, "bg-success/40"],
  [6, "bg-success/60"],
  [10, "bg-success/85"],
];

/** The day's total actions (the wire type carries the four counts, not a sum). */
function dayTotal(day: ActivityHeatmapDay): number {
  return day.applications + day.interviews + day.replies + day.aiCalls;
}

function intensity(total: number): string {
  // Zero is its own answer: a quiet day reads as quiet, not as the ramp's first step.
  if (total === 0) return "bg-muted/40";
  for (const [min, cls] of RAMP) {
    if (total < min) return cls;
  }
  return RAMP[RAMP.length - 1][1];
}

/** Monday-first weekday index (0 = Monday) of an ISO date string. */
function weekdayIndex(iso: string): number {
  const day = new Date(`${iso}T00:00:00Z`).getUTCDay(); // 0 = Sunday
  return (day + 6) % 7;
}

function monthLabel(iso: string, locale: string): string {
  return new Intl.DateTimeFormat(locale === "zh" ? "zh-CN" : "en", {
    month: "short",
    timeZone: "UTC",
  }).format(new Date(`${iso}T00:00:00Z`));
}

function Cell({
  day,
  tooltip,
}: {
  day: ActivityHeatmapDay | null;
  tooltip: string;
}) {
  return (
    <div
      role="img"
      aria-label={day ? tooltip : undefined}
      title={day ? tooltip : undefined}
      className={cn(
        "size-[11px] rounded-[3px] transition-transform duration-100 hover:scale-125 hover:ring-1 hover:ring-foreground/30",
        day ? intensity(dayTotal(day)) : "bg-transparent",
      )}
    />
  );
}

export function ActivityHeatmap({ days = 182 }: { days?: number }) {
  const { t, locale } = useLocale();
  const heatmap = useActivityHeatmap(days);
  const data = heatmap.data;

  return (
    <Card>
      <CardHeader className="gap-1.5">
        <CardTitle className="flex items-center gap-2 text-base">
          <Flame className="size-4 text-warning" aria-hidden />
          {t("dashboard.heatmapTitle")}
        </CardTitle>
        <CardDescription>{t("dashboard.heatmapDescription")}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {heatmap.isPending && <Skeleton className="h-24 rounded-lg" />}

        {heatmap.isError && (
          <p className="text-sm text-muted-foreground">{t("dashboard.heatmapUnavailable")}</p>
        )}

        {data && (
          <>
            <div className="flex flex-wrap items-center gap-x-5 gap-y-1 text-xs text-muted-foreground">
              <span className="flex items-center gap-1.5">
                <Flame aria-hidden className="size-3.5 text-warning" />
                {t("dashboard.heatmapCurrentStreak")}
                <span className="font-semibold text-foreground tabular-nums">
                  {data.streak.current}
                </span>
              </span>
              <span className="flex items-center gap-1.5">
                {t("dashboard.heatmapLongestStreak")}
                <span className="font-semibold text-foreground tabular-nums">
                  {data.streak.longest}
                </span>
              </span>
              <span className="flex items-center gap-1.5">
                {t("dashboard.heatmapTotal")}
                <span className="font-semibold text-foreground tabular-nums">
                  {data.grandTotal}
                </span>
              </span>
            </div>

            {data.grid.every((d) => dayTotal(d) === 0) ? (
              <p className="text-sm text-muted-foreground">{t("dashboard.heatmapEmpty")}</p>
            ) : (
              <div className="overflow-x-auto pb-1">
                <div className="min-w-fit">
                  {/* Month labels: one per column that first touches a new month.
                      A week column is 11px cell + 3px gap = 14px. */}
                  <div className="relative ml-[14px] h-3.5" aria-hidden>
                    {monthLabels(data.grid, (iso) => monthLabel(iso, locale)).map((m) => (
                      <span
                        key={`${m.text}-${m.column}`}
                        className="absolute text-2xs leading-none text-muted-foreground"
                        style={{ left: `${m.column * 14}px` }}
                      >
                        {m.text}
                      </span>
                    ))}
                  </div>
                  <div className="flex" style={{ gap: "3px" }}>
                    {gridColumns(data.grid).map((column, ci) => (
                      <div key={`week-${ci}`} className="flex flex-col" style={{ gap: "3px" }}>
                        {column.map((day) => (
                          <Cell
                            key={day?.date ?? `pad-${ci}`}
                            day={day}
                            tooltip={cellTooltip(day, t)}
                          />
                        ))}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            <div className="flex items-center justify-between text-2xs text-muted-foreground">
              <span className="flex items-center gap-1">
                {t("dashboard.heatmapLess")}
                {[0, 1, 3, 6, 10].map((min) => (
                  <span
                    key={min}
                    aria-hidden
                    className={cn("size-[10px] rounded-[3px]", min === 0 ? "bg-muted/50" : intensity(min))}
                  />
                ))}
                {t("dashboard.heatmapMore")}
                <span className="sr-only">{t("dashboard.heatmapLegendAria")}</span>
              </span>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}

/** Slice the dense day list into week columns of seven (padded at both ends). */
function gridColumns(grid: ActivityHeatmapDay[]): Array<Array<ActivityHeatmapDay | null>> {
  const lead = weekdayIndex(grid[0].date);
  const cells: Array<ActivityHeatmapDay | null> = [
    ...Array.from({ length: lead }, () => null),
    ...grid,
  ];
  const weeks: Array<Array<ActivityHeatmapDay | null>> = [];
  for (let i = 0; i < cells.length; i += WEEKDAYS) {
    weeks.push(cells.slice(i, i + WEEKDAYS));
  }
  return weeks;
}

/** The column index each new month first appears in, paired with its label. */
function monthLabels(
  grid: ActivityHeatmapDay[],
  label: (iso: string) => string,
): Array<{ column: number; text: string }> {
  const out: Array<{ column: number; text: string }> = [];
  let lastMonth = "";
  grid.forEach((day, i) => {
    const month = day.date.slice(0, 7);
    if (month !== lastMonth) {
      lastMonth = month;
      out.push({ column: Math.floor((weekdayIndex(grid[0].date) + i) / WEEKDAYS), text: label(day.date) });
    }
  });
  return out;
}

function cellTooltip(
  day: ActivityHeatmapDay | null,
  t: (key: string, vars?: Record<string, string | number>) => string,
): string {
  if (!day) return "";
  const parts: string[] = [day.date];
  if (day.applications) parts.push(t("dashboard.applications", { count: day.applications }));
  if (day.interviews) parts.push(t("dashboard.interviews", { count: day.interviews }));
  if (day.replies) parts.push(t("dashboard.replies", { count: day.replies }));
  if (day.aiCalls) parts.push(t("dashboard.heatmapAiCalls", { count: day.aiCalls }));
  return parts.join(" · ") || t("dashboard.heatmapQuietDay");
}
