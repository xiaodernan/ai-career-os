"use client";

import * as React from "react";
import { AudioLines, Lightbulb } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useLocale } from "@/lib/i18n/locale-context";
import { analyzeAnswers } from "@/lib/answer-echo";

/**
 * Epic 385 — the echo card. The evaluator is the model's reading of an answer; this
 * is the reader's own reading, computed in the browser from the answers already on
 * the page. It renders only once a session has answered something, and it never
 * claims more than arithmetic: length, sentence size, fillers, figures, and whether
 * the voice is "I" or "we".
 */
export function AnswerEchoCard({ answers }: { answers: string[] }) {
  const { t } = useLocale();
  const echo = React.useMemo(() => analyzeAnswers(answers), [answers]);

  if (echo.answers === 0) return null;

  const stats: { key: string; label: string; value: string | number; title?: string }[] = [
    { key: "answers", label: t("interviews.detail.echoAnswers"), value: echo.answers },
    { key: "units", label: t("interviews.detail.echoAvgSize"), value: echo.avgUnits },
    { key: "sentences", label: t("interviews.detail.echoAvgSentence"), value: echo.avgSentence },
    { key: "fillers", label: t("interviews.detail.echoFillers"), value: echo.fillerTotal },
    { key: "numbers", label: t("interviews.detail.echoNumbers"), value: echo.numbers },
    {
      key: "ownership",
      label: t("interviews.detail.echoOwnership"),
      value: echo.ownership == null ? "—" : `${Math.round(echo.ownership * 100)}%`,
      title: t("interviews.detail.echoOwnershipTitle"),
    },
  ];

  return (
    <Card data-testid="answer-echo-card" className="border-primary/15 bg-gradient-to-br from-primary/[0.04] via-card to-card">
      <CardHeader className="flex flex-row items-start gap-4 space-y-0 pb-3">
        <div className="flex size-10 shrink-0 items-center justify-center rounded-xl border border-primary/25 bg-primary/10 text-primary">
          <AudioLines aria-hidden className="size-5" />
        </div>
        <div className="min-w-0">
          <p className="text-2xs font-semibold uppercase tracking-widest text-primary">
            {t("interviews.detail.echoEyebrow")}
          </p>
          <CardTitle className="mt-0.5 text-base">{t("interviews.detail.echoTitle")}</CardTitle>
          <CardDescription>{t("interviews.detail.echoDescription")}</CardDescription>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <dl className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          {stats.map((stat) => (
            <div key={stat.key} className="rounded-lg border border-border/60 bg-card/60 px-3 py-2">
              <dt className="text-2xs text-muted-foreground" title={stat.title}>
                {stat.label}
              </dt>
              <dd className="font-mono text-lg tabular-nums text-foreground">{stat.value}</dd>
            </div>
          ))}
        </dl>

        {echo.fillerTotal > 0 && (
          <div className="space-y-1.5">
            <p className="text-2xs font-medium uppercase tracking-wide text-muted-foreground">
              {t("interviews.detail.echoRepeated")}
            </p>
            <ul className="flex flex-wrap gap-1.5">
              {echo.fillers.map((filler) => (
                <li
                  key={filler.term}
                  className="rounded-full border border-border/70 bg-background/70 px-2.5 py-1 font-mono text-2xs text-foreground/90"
                >
                  {filler.term} × {filler.count}
                </li>
              ))}
            </ul>
          </div>
        )}

        <ul className="space-y-2">
          {echo.nudges.length === 0 ? (
            <li className="flex items-start gap-2 text-sm leading-relaxed text-muted-foreground">
              <Lightbulb aria-hidden className="mt-0.5 size-4 shrink-0 text-primary" />
              {t("interviews.detail.echoClear")}
            </li>
          ) : (
            echo.nudges.map((nudge) => (
              <li
                key={nudge.key}
                className={
                  nudge.watch
                    ? "flex items-start gap-2 text-sm leading-relaxed text-warning"
                    : "flex items-start gap-2 text-sm leading-relaxed text-muted-foreground"
                }
              >
                <Lightbulb aria-hidden className="mt-0.5 size-4 shrink-0" />
                <span>{t(nudge.key, nudge.vars)}</span>
              </li>
            ))
          )}
        </ul>

        <p className="text-2xs leading-relaxed text-muted-foreground">
          {t("interviews.detail.echoFootnote")}
        </p>
      </CardContent>
    </Card>
  );
}
