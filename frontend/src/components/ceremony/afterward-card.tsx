"use client";

/**
 * Afterward (Epic 276) — what the reader carries out, and why it is heavier.
 *
 * The closing page already says: the loop happened, the ledger counted. This
 * is the last honest card on it — the one that doesn't celebrate the outcome
 * and doesn't forgive the effort. It says, flatly, what the reader knocked
 * on, what they rehearsed, how many days they showed up — before anything
 * was called a win or a not-yet.
 *
 * Renders nothing when the account has none of those three. A reader with
 * zero applications and zero interviews deserves the silence; they don't get
 * a card attesting to an arc that didn't happen.
 */

import * as React from "react";
import { CalendarCheck, DoorOpen, Hammer } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { useApplications, useInterviewSessions } from "@/lib/hooks/resources";
import { useActivityHeatmap } from "@/lib/hooks/monitoring";
import { useLocale } from "@/lib/i18n/locale-context";

export function AfterwardCard() {
  const { t } = useLocale();
  const applications = useApplications({ size: 1, page: 0 });
  const interviews = useInterviewSessions({ size: 1, page: 0 });
  const heatmap = useActivityHeatmap(366);

  const apps = applications.data?.total ?? 0;
  const rehearsed = interviews.data?.total ?? 0;
  const showed = (heatmap.data?.grid ?? []).filter(
    (day) => day.applications + day.interviews + day.replies + day.aiCalls > 0
  ).length;

  if (apps === 0 && rehearsed === 0 && showed === 0) return null;

  const items = [
    { key: "apps", Icon: DoorOpen, labelKey: "ceremony.afterwardK1Label", textKey: "ceremony.afterwardK1Text", count: apps },
    { key: "interviews", Icon: Hammer, labelKey: "ceremony.afterwardK2Label", textKey: "ceremony.afterwardK2Text", count: rehearsed },
    { key: "days", Icon: CalendarCheck, labelKey: "ceremony.afterwardK3Label", textKey: "ceremony.afterwardK3Text", count: showed },
  ];

  return (
    <Card className="overflow-hidden border-violet-300/30 bg-gradient-to-br from-violet-50/60 via-card to-card shadow-card print:break-inside-avoid">
      <CardContent className="relative space-y-6 p-6 sm:p-8">
        <span
          aria-hidden
          className="pointer-events-none absolute -right-20 -top-20 h-56 w-56 rounded-full print:hidden"
          style={{
            background:
              "radial-gradient(closest-side, color-mix(in oklch, var(--primary) 18%, transparent), transparent)",
          }}
        />
        <div className="relative">
          <p className="text-2xs font-semibold uppercase tracking-widest text-primary">
            {t("ceremony.afterwardEyebrow")}
          </p>
          <h3 className="mt-1 font-serif text-2xl font-semibold tracking-tight sm:text-3xl">
            {t("ceremony.afterwardTitle")}
          </h3>
          <p className="mt-2 max-w-3xl text-sm leading-relaxed text-muted-foreground">
            {t("ceremony.afterwardIntro")}
          </p>
        </div>
        <ol className="relative mt-6 grid gap-3 sm:grid-cols-3">
          {items.map(({ key, Icon, labelKey, textKey, count }) => (
            <li
              key={key}
              className="flex flex-col gap-2 rounded-2xl border border-border/60 bg-card/70 p-4 backdrop-blur-sm"
            >
              <span className="flex size-9 items-center justify-center rounded-xl border border-primary/25 bg-primary/10 text-primary">
                <Icon className="size-5" aria-hidden />
              </span>
              <span className="text-2xs font-semibold uppercase tracking-widest text-muted-foreground">
                {t(labelKey)}
              </span>
              <span className="text-2xl font-semibold tabular-nums">{count.toLocaleString()}</span>
              <span className="text-2xs leading-relaxed text-muted-foreground">
                {t(textKey, { count })}
              </span>
            </li>
          ))}
        </ol>
        <p className="relative mt-6 border-t border-border/60 pt-5 text-sm italic leading-relaxed text-muted-foreground">
          {t("ceremony.afterwardFootnote")}
        </p>
      </CardContent>
    </Card>
  );
}
