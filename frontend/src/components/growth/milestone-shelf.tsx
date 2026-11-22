"use client";

import * as React from "react";
import { Award, Trophy } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { useMilestones } from "@/lib/hooks/monitoring";
import { useLocale } from "@/lib/i18n/locale-context";
import { cn } from "@/lib/utils";

/**
 * The milestone shelf (Epic 273): the reader's progress as a badge strip on the
 * growth page. The backend answers keys and numbers only — the words live in this
 * file's locale tables — so a badge earned reads in the reader's language and the
 * keys can never carry a sentence the other locale disagrees with.
 *
 * Earned badges are full-color with their own label; working badges show the
 * progress/target on a bar, because the point of the shelf is the NEXT one: a strip
 * of only trophies tells a reader nothing about what to do this week.
 */

/** The words live in the locale table (`growth.milestone_<key>_earned` / `_working`)
 *  so a Chinese reader never sees an English sentence hard-coded in this source —
 *  see the copy-census gate. */
function milestoneLabel(t: (key: string) => string, key: string, done: boolean): string {
  const suffix = done ? "earned" : "working";
  const fullKey = `growth.milestone_${key}_${suffix}`;
  // A milestone the backend adds before the locale table knows it falls back to
  // its own key rather than showing an empty badge.
  return t(fullKey) === fullKey ? key : t(fullKey);
}

export function MilestoneShelf() {
  const { t } = useLocale();
  const shelf = useMilestones();
  const data = shelf.data;
  const earnedCount = data?.milestones.filter((m) => m.done).length ?? 0;

  return (
    <Card>
      <CardHeader className="gap-1.5">
        <CardTitle className="flex items-center gap-2 text-base">
          <Trophy className="size-4 text-warning" aria-hidden />
          {t("growth.milestonesTitle")}
          {data && (
            <Badge variant="secondary" className="font-normal">
              {earnedCount}/{data.milestones.length}
            </Badge>
          )}
        </CardTitle>
        <CardDescription>{t("growth.milestonesDescription")}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {shelf.isPending && <Skeleton className="h-28 rounded-lg" />}
        {shelf.isError && (
          <p className="text-sm text-muted-foreground">{t("growth.milestonesUnavailable")}</p>
        )}
        {data && (
          <ul className="grid gap-2 sm:grid-cols-2">
            {data.milestones.map((m) => {
              const label = milestoneLabel(t, m.key, m.done);
              const pct = m.target ? Math.min(100, Math.round(((m.progress ?? 0) / m.target) * 100)) : 0;
              return (
                <li
                  key={m.key}
                  className={cn(
                    "rounded-lg border p-3 transition-colors",
                    m.done ? "border-warning/40 bg-warning/5" : "border-border/60",
                  )}
                >
                  <div className="flex items-center justify-between gap-2">
                    <p className="flex items-center gap-2 text-sm font-medium">
                      <Award
                        aria-hidden
                        className={cn("size-4", m.done ? "text-warning" : "text-muted-foreground/40")}
                      />
                      <span className="min-w-0 truncate">{label}</span>
                    </p>
                    {m.done && (
                      <Badge variant="warning" className="shrink-0 font-normal">
                        {t("growth.milestoneEarned")}
                      </Badge>
                    )}
                  </div>
                  {!m.done && m.target != null && m.target > 1 && (
                    <div className="mt-2 space-y-1">
                      <div
                        className="h-1.5 overflow-hidden rounded-full bg-muted"
                        role="progressbar"
                        aria-valuenow={m.progress ?? 0}
                        aria-valuemin={0}
                        aria-valuemax={m.target}
                      >
                        <div
                          className="h-full rounded-full bg-primary/60 transition-all duration-300"
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                      <p className="text-2xs text-muted-foreground tabular-nums">
                        {t("growth.milestoneProgress", { progress: m.progress ?? 0, target: m.target })}
                      </p>
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
        )}
        {data && (
          <p className="text-2xs text-muted-foreground tabular-nums">
            {t("growth.milestoneCounters", {
              applications: data.counters.applications,
              interviews: data.counters.interviewsCompleted,
              offers: data.counters.offers,
            })}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
