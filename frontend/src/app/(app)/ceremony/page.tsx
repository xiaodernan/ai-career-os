"use client";

import * as React from "react";
import { Calendar, Feather, FileText, Inbox, Mail, PenLine, Printer } from "lucide-react";
import { PageHeader } from "@/components/common/page-header";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  useApplications,
  useInterviewSessions,
  useKnowledgeNotes,
  useOfferShelf,
} from "@/lib/hooks/resources";
import { useLetters } from "@/lib/hooks/letters";
import { useActivityHeatmap } from "@/lib/hooks/monitoring";
import { useLocale } from "@/lib/i18n/locale-context";
import { formatDateOnly } from "@/lib/format";

/**
 * The closing ceremony (Epic 212) — the page that says what the loop was.
 *
 * The product records everything: the applications, the calls, the interviews, the
 * letters you kept. The timeline says everything in order; this page steps back,
 * says it in one frame, and lets the reader walk out proud. Every number is bound
 * to a real route answer — never invented — and the letter between the two closing
 * frames is addressed to the reader by the product's own editor.
 *
 * The print button uses the browser's own PDF path. The page is tuned to one column
 * on paper: the hero, the stats, the address, the farewell. Nothing here leaves the
 * server; it is a reading of what the account already did.
 */
export default function CeremonyPage() {
  const { t, locale } = useLocale();
  const applications = useApplications({ size: 20, page: 0 });
  const interviews = useInterviewSessions({ size: 1, page: 0 });
  const offers = useOfferShelf();
  const letters = useLetters();
  const notes = useKnowledgeNotes({ size: 1, page: 0 });
  const heatmap = useActivityHeatmap(366);

  const appCount = applications.data?.total ?? 0;
  const interviewCount = interviews.data?.total ?? 0;
  const offerCount = offers.data?.items?.length ?? 0;
  const letterCount = letters.data?.total ?? 0;
  const noteCount = notes.data?.total ?? 0;
  const daysShowed = (heatmap.data?.grid ?? []).filter(
    (day) => day.applications + day.interviews + day.replies + day.aiCalls > 0
  ).length;
  const today = new Date().toISOString().slice(0, 10);
  const grandTotal = heatmap.data?.grandTotal ?? 0;

  const accepted = (offers.data?.items ?? []).find((row) => row.decision === "accepted") ?? null;
  const loading = applications.isPending || interviews.isPending || offers.isPending;

  const tiles = [
    {
      key: "apps",
      label: t("ceremony.statApplications"),
      value: String(appCount),
      icon: Inbox,
      accent: "text-primary border-primary/30 bg-primary/10",
    },
    {
      key: "interviews",
      label: t("ceremony.statInterviews"),
      value: String(interviewCount),
      icon: Calendar,
      accent: "text-success border-success/30 bg-success/10",
    },
    {
      key: "offers",
      label: t("ceremony.statOffers"),
      value: String(offerCount),
      icon: FileText,
      accent: "text-warning border-warning/30 bg-warning/10",
    },
    {
      key: "letters",
      label: t("ceremony.statLetters"),
      value: String(letterCount),
      icon: Mail,
      accent: "text-primary border-primary/30 bg-primary/10",
    },
    {
      key: "notes",
      label: t("ceremony.statNotes"),
      value: String(noteCount),
      icon: PenLine,
      accent: "text-muted-foreground border-border/60 bg-muted",
    },
    {
      key: "days",
      label: t("ceremony.statDays"),
      value: String(daysShowed),
      icon: Feather,
      accent: "text-primary border-primary/30 bg-primary/10",
    },
  ];

  return (
    <div className="flex flex-col gap-8 print:gap-0">
      <div className="print:hidden">
        <PageHeader frontDoor title={t("ceremony.title")} description={t("ceremony.description")} />
      </div>
      <Card className="relative overflow-hidden border-primary/20 bg-gradient-to-b from-violet-50/60 via-background to-background shadow-card print:break-inside-avoid print:border-0 print:shadow-none">
        <CardContent className="relative space-y-10 p-6 sm:p-10">
          <span
            aria-hidden
            className="pointer-events-none absolute -right-32 -top-32 h-80 w-80 rounded-full"
            style={{
              background:
                "radial-gradient(closest-side, color-mix(in oklch, var(--primary) 22%, transparent), transparent)",
            }}
          />
          <span
            aria-hidden
            className="pointer-events-none absolute -bottom-32 -left-32 h-80 w-80 rounded-full"
            style={{
              background:
                "radial-gradient(closest-side, color-mix(in oklch, var(--accent) 18%, transparent), transparent)",
            }}
          />
          <div className="relative space-y-6">
            <div className="flex flex-wrap items-baseline justify-between gap-3 text-xs uppercase tracking-[0.28em] text-primary/80">
              <span>{t("ceremony.eyebrow")}</span>
              <span className="normal-case tracking-normal text-muted-foreground">
                {t("ceremony.dateLine", { date: formatDateOnly(today, locale) })}
              </span>
            </div>
            <h1 className="max-w-3xl text-4xl font-semibold leading-[1.05] tracking-tight sm:text-5xl lg:text-6xl">
              {t("ceremony.title")}
            </h1>
            <p className="max-w-2xl text-base text-muted-foreground">{t("ceremony.epigraph")}</p>
          </div>

          <div className="relative grid grid-cols-2 gap-3 sm:grid-cols-3 sm:gap-4">
            {tiles.map((tile) => {
              const Icon = tile.icon;
              return (
                <div
                  key={tile.key}
                  className={`flex flex-col gap-1 rounded-2xl border p-4 transition-transform duration-200 ${tile.accent}`}
                >
                  <Icon aria-hidden className="size-4 opacity-80" />
                  <span className="text-2xl font-semibold tabular-nums sm:text-3xl">{tile.value}</span>
                  <span className="text-2xs uppercase tracking-wide text-current/80">{tile.label}</span>
                </div>
              );
            })}
          </div>

          <div className="relative grid gap-6 lg:grid-cols-5">
            <div className="space-y-4 lg:col-span-3">
              <h2 className="font-serif text-xl font-semibold tracking-tight">{t("ceremony.letterTitle")}</h2>
              {loading ? (
                <div className="space-y-2" aria-hidden="true">
                  <div className="h-5 w-3/4 animate-pulse rounded bg-muted" />
                  <div className="h-4 w-full animate-pulse rounded bg-muted" />
                  <div className="h-4 w-5/6 animate-pulse rounded bg-muted" />
                </div>
              ) : (
                <>
                  <p className="text-base leading-relaxed text-foreground/90">
                    {t("ceremony.letterPara1", {
                      applications: appCount,
                      interviews: interviewCount,
                      notes: noteCount,
                      letters: letterCount,
                    })}
                  </p>
                  <p className="text-base leading-relaxed text-foreground/90">
                    {accepted
                      ? t("ceremony.letterPara2Accepted", { offers: offerCount })
                      : t("ceremony.letterPara2Pending", { offers: offerCount })}
                  </p>
                  <p className="text-base leading-relaxed text-foreground/90">{t("ceremony.letterPara3")}</p>
                </>
              )}
            </div>
            <div className="space-y-4 rounded-2xl border border-border/60 bg-card/60 p-5 backdrop-blur-sm lg:col-span-2 print:break-inside-avoid">
              <h3 className="text-base font-semibold tracking-tight">{t("ceremony.codaTitle")}</h3>
              <ol className="flex flex-col gap-4 text-sm leading-relaxed text-foreground/90">
                <li className="flex gap-3">
                  <span className="flex size-6 shrink-0 items-center justify-center rounded-full border border-primary/40 bg-primary/10 text-2xs font-semibold text-primary tabular-nums">1</span>
                  <span>{t("ceremony.coda1")}</span>
                </li>
                <li className="flex gap-3">
                  <span className="flex size-6 shrink-0 items-center justify-center rounded-full border border-primary/40 bg-primary/10 text-2xs font-semibold text-primary tabular-nums">2</span>
                  <span>{t("ceremony.coda2")}</span>
                </li>
                <li className="flex gap-3">
                  <span className="flex size-6 shrink-0 items-center justify-center rounded-full border border-primary/40 bg-primary/10 text-2xs font-semibold text-primary tabular-nums">3</span>
                  <span>{t("ceremony.coda3")}</span>
                </li>
              </ol>
              <p className="pt-3 text-right font-serif text-sm italic text-muted-foreground">{t("ceremony.codaSign")}</p>
              <div className="border-t border-border/60 pt-4">
                <Button variant="outline" size="sm" onClick={() => window.print()} className="print:hidden">
                  <Printer aria-hidden className="size-4" />
                  <span>{t("ceremony.print")}</span>
                </Button>
                <p className="mt-2 text-2xs text-muted-foreground">{t("ceremony.printHint")}</p>
                <p className="mt-3 text-2xs text-muted-foreground">
                  {t("ceremony.grandTotal", {
                    total: grandTotal,
                    days: daysShowed,
                    letters: letterCount,
                  })}
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
