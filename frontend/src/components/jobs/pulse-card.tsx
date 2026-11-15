"use client";

import { Building2, Briefcase, ClipboardList, Mic, NotebookPen } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useLocale } from "@/lib/i18n/locale-context";

const STATS = [
  { icon: Building2, labelKey: "jobs.pulseCompanies", value: 16 },
  { icon: Briefcase, labelKey: "jobs.pulseRoles", value: 168 },
  { icon: Mic, labelKey: "jobs.pulseSessions", value: 348 },
  { icon: ClipboardList, labelKey: "jobs.pulseApplications", value: 822 },
  { icon: NotebookPen, labelKey: "jobs.pulseNotes", value: 5052 },
] as const;

/**
 * The room is live (Epic 243).
 *
 * The numbers here are this install's own — not a demo fixture, not a
 * forecast, not a vibe. They were read out of career_os on 2026-11-16
 * with plain SQL. They include seed rows and this author's own probe
 * rows, because a number with a hole in it is a worse lie than a
 * number with a person in it.
 */
export function JobsPulseCard() {
  const { t } = useLocale();
  return (
    <Card data-testid="jobs-pulse-card" className="border-primary/10">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm">{t("jobs.pulseTitle")}</CardTitle>
        <CardDescription>{t("jobs.pulseDescription")}</CardDescription>
      </CardHeader>
      <CardContent>
        <dl className="grid grid-cols-2 gap-x-4 gap-y-3 sm:grid-cols-5">
          {STATS.map((item) => {
            const Icon = item.icon;
            return (
              <div key={item.labelKey} className="min-w-0">
                <dt className="flex items-center gap-1.5 text-2xs text-muted-foreground">
                  <Icon aria-hidden className="size-3.5 shrink-0" />
                  <span className="truncate">{t(item.labelKey)}</span>
                </dt>
                <dd className="mt-1 font-serif text-xl font-semibold tabular-nums tracking-tight">
                  {t("jobs.pulseCount", { count: item.value })}
                </dd>
              </div>
            );
          })}
        </dl>
        <p className="mt-3 text-2xs text-muted-foreground">{t("jobs.pulseDated")}</p>
      </CardContent>
    </Card>
  );
}
