"use client";

import * as React from "react";
import Link from "next/link";
import {
  CalendarClock,
  Check,
  Feather,
  FileText,
  Handshake,
  MailOpen,
  Map,
  Mic,
  RotateCcw,
  Sparkles,
  Target,
  TrendingUp,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useLocale } from "@/lib/i18n/locale-context";
import {
  TOUR_HREFS,
  clearTourVisits,
  readTourVisits,
  tourProgress,
  type TourRoute,
} from "@/lib/tour";

const ROW_ICONS: Record<TourRoute, React.ComponentType<{ className?: string; "aria-hidden"?: boolean }>> = {
  "/resumes": FileText,
  "/studio": Target,
  "/growth": TrendingUp,
  "/letters": Feather,
  "/interviews": Mic,
  "/applications": CalendarClock,
  "/replies": MailOpen,
  "/offers": Handshake,
  "/ceremony": Sparkles,
};

/** The nav namespace key for each caller's sidebar label. */
const NAV_LABEL: Record<TourRoute, string> = {
  "/resumes": "nav.resumes",
  "/studio": "nav.studio",
  "/growth": "nav.growth",
  "/letters": "nav.letters",
  "/interviews": "nav.interviews",
  "/applications": "nav.applications",
  "/replies": "nav.replies",
  "/offers": "nav.offers",
  "/ceremony": "nav.ceremony",
};

/** The description-line key beside it. */
const NAV_DESCRIPTION: Record<TourRoute, string> = {
  "/resumes": "navDescriptions.resumes",
  "/studio": "navDescriptions.studio",
  "/growth": "navDescriptions.growth",
  "/letters": "navDescriptions.letters",
  "/interviews": "navDescriptions.interviews",
  "/applications": "navDescriptions.applications",
  "/replies": "navDescriptions.replies",
  "/offers": "navDescriptions.offers",
  "/ceremony": "navDescriptions.ceremony",
};

/**
 * The nine quests (Epic 235) — the dashboard's walking tour.
 *
 * Nine rooms, checked off as the reader opens them (the marker writes the
 * visit set; this card reads it). The tour exists so a new person learns the
 * product by walking it, at their own pace, in their own language. Nothing
 * here scores the reader and nothing leaves the browser; the badge is the
 * reader's, the same as the ledger.
 */
export function NineQuestsCard() {
  const { t } = useLocale();
  const [visited, setVisited] = React.useState<TourRoute[]>(() =>
    readTourVisits(typeof window === "undefined" ? null : window.localStorage)
  );
  const { done, total } = tourProgress(visited);
  const complete = done === total;

  return (
    <Card data-testid="nine-quests-card" className="border-primary/15 shadow-card">
      <CardHeader className="flex flex-row items-start gap-4 space-y-0">
        <div className="flex size-10 shrink-0 items-center justify-center rounded-xl border border-primary/25 bg-primary/10 text-primary">
          <Map aria-hidden className="size-5" />
        </div>
        <div className="min-w-0">
          <CardTitle className="text-base">{t("dashboard.nineQuestsTitle")}</CardTitle>
          <CardDescription>{t("dashboard.nineQuestsIntro")}</CardDescription>
        </div>
        {done > 0 && (
          <Button
            variant="ghost"
            size="icon-sm"
            className="ml-auto shrink-0"
            onClick={() => {
              clearTourVisits();
              setVisited([]);
            }}
            aria-label={t("dashboard.nineQuestsReset")}
          >
            <RotateCcw aria-hidden className="size-4" />
          </Button>
        )}
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <div className="flex items-baseline justify-between gap-3">
            <p className="text-2xs font-semibold uppercase tracking-widest text-muted-foreground">
              {t("dashboard.nineQuestsProgress", { done, total })}
            </p>
            {complete && <p className="text-2xs font-semibold uppercase tracking-widest text-success">{t("dashboard.nineQuestsClear")}</p>}
          </div>
          <div
            className="h-1.5 w-full overflow-hidden rounded-full bg-muted"
            role="progressbar"
            aria-valuenow={done}
            aria-valuemin={0}
            aria-valuemax={total}
          >
            <div
              className="h-full rounded-full bg-primary transition-all duration-500"
              style={{ width: `${(done / total) * 100}%` }}
            />
          </div>
        </div>
        <ol className="grid gap-2 sm:grid-cols-3">
          {TOUR_HREFS.map((route) => {
            const Icon = ROW_ICONS[route];
            const did = visited.includes(route);
            return (
              <li key={route}>
                <Link
                  href={route}
                  aria-current={did ? "true" : undefined}
                  className={cn(
                    "group flex h-full items-center gap-2.5 rounded-xl border px-3 py-2 transition-all duration-200 focus-visible:ring-[3px] focus-visible:ring-primary/30",
                    did
                      ? "border-success/25 bg-success/5"
                      : "border-border/60 bg-card/60 hover:border-primary/30 hover:bg-accent/40"
                  )}
                >
                  <span
                    aria-hidden
                    className={cn(
                      "flex size-8 shrink-0 items-center justify-center rounded-lg ring-1 ring-inset transition-colors duration-200",
                      did
                        ? "bg-success/15 text-success ring-success/25"
                        : "bg-primary/10 text-primary ring-primary/15 group-hover:bg-primary/15"
                    )}
                  >
                    {did ? <Check className="size-4" /> : <Icon className="size-4" />}
                  </span>
                  <span className="min-w-0">
                    <span className="block truncate text-xs font-semibold leading-tight">
                      {t(NAV_LABEL[route])}
                    </span>
                    <span className="mt-0.5 block truncate text-2xs leading-tight text-muted-foreground">
                      {t(NAV_DESCRIPTION[route])}
                    </span>
                  </span>
                </Link>
              </li>
            );
          })}
        </ol>
        {complete && (
          <p role="status" className="rounded-xl border border-success/25 bg-success/10 px-4 py-3 text-sm leading-relaxed text-foreground/90">
            {t("dashboard.nineQuestsDone")}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
