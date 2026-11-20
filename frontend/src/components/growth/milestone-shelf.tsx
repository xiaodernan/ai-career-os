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

/** key → [earned label, working label]; the keys are the backend's contract. */
const MILESTONE_WORDS: Record<string, [string, string]> = {
  first_step: ["First application filed", "File your first application"],
  ten_steps: ["Ten applications filed", "File 10 applications"],
  fifty_steps: ["Fifty applications filed", "File 50 applications"],
  grounded: ["First match computed", "Run your first match"],
  first_rehearsal: ["First rehearsal done", "Hold your first rehearsal"],
  five_rehearsals: ["Five rehearsals done", "Hold 5 rehearsals"],
  letter_wright: ["Three letters kept", "Keep 3 letters"],
  first_offer: ["First offer received", "Receive your first offer"],
  shelf_full: ["Three offers on the shelf", "Hold 3 offers at once"],
  streak_week: ["A seven-day streak", "Act 7 days in a row"],
};

export function MilestoneShelf() {
  const { t, locale } = useLocale();
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
              const words = MILESTONE_WORDS[m.key] ?? [m.key, m.key];
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
                      <span className="min-w-0 truncate">
                        {m.done ? words[0] : words[1]}
                      </span>
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
