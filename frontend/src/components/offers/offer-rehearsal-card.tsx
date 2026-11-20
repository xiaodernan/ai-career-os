"use client";

import * as React from "react";
import { Check, RotateCcw } from "lucide-react";
import { cn } from "@/lib/utils";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Hint } from "@/components/ui/hint";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { useLocale } from "@/lib/i18n/locale-context";
import {
  MAX_REHEARSAL_SCORE,
  REHEARSAL_PUSHES,
  answered,
  clearRehearsal,
  loadRehearsal,
  saveRehearsal,
  scoreOf,
  totalScore,
  verdictBand,
  type RehearsalState,
} from "@/lib/offers/rehearsal";

/**
 * The rehearsal room (Epic 227) — the ask, before the offer.
 *
 * The shelf ranks offers by one number; this room rehearses the conversation
 * that follows it. Three hiring-manager pushes, three replies each, a verdict
 * at nine. Nothing here is a claim about the product — it is the shape every
 * real salary conversation takes, rehearsed first where fumbles are free.
 * The chosen sentence lives in this browser only, like the decision ledger.
 */
const FEEDBACK_KEY = (score: number): string =>
  score === 3
    ? "offers.rehearsalFeedbackEvidence"
    : score >= 2
      ? "offers.rehearsalFeedbackHold"
      : score >= 1
        ? "offers.rehearsalFeedbackGap"
        : "offers.rehearsalFeedbackConcede";

const VERDICT_KEY = (band: string): string => `offers.rehearsalVerdict${band.charAt(0).toUpperCase()}${band.slice(1)}`;

export function OfferRehearsalCard() {
  const { t } = useLocale();
  const [state, setState] = React.useState<RehearsalState>(() => loadRehearsal(
    typeof window === "undefined" ? null : window.localStorage
  ));
  const [revealed, setRevealed] = React.useState<Record<string, boolean>>({});
  const [step, setStep] = React.useState(0);

  const done = answered(state);
  const current = REHEARSAL_PUSHES[step];
  const picked = current ? state.scores[current.id] : undefined;
  const total = totalScore(state);
  const band = verdictBand(total);
  const isLast = step === REHEARSAL_PUSHES.length - 1;

  const pick = (pushId: string, replyId: string) => {
    const nextScores = { ...state.scores, [pushId]: replyId };
    setState((prev) => ({ ...prev, scores: nextScores }));
    setRevealed((prev) => ({ ...prev, [pushId]: true }));
    saveRehearsal({ scores: nextScores, sentence: state.sentence });
  };

  const setSentence = (event: React.ChangeEvent<HTMLTextAreaElement>) => {
    setState((prev) => {
      const next = { ...prev, sentence: event.target.value };
      saveRehearsal(next);
      return next;
    });
  };

  const reset = () => {
    clearRehearsal();
    setState({ scores: {}, sentence: "" });
    setRevealed({});
    setStep(0);
  };

  const advance = () => setStep((currentStep) => Math.min(currentStep + 1, REHEARSAL_PUSHES.length - 1));

  return (
    <Card
      data-testid="rehearsal-room"
      className="overflow-hidden border-warning/25 bg-gradient-to-br from-warning/5 via-card to-card shadow-card print:break-inside-avoid"
    >
      <CardHeader className="flex flex-row items-start gap-4 space-y-0">
        <div className="flex size-10 shrink-0 items-center justify-center rounded-xl border border-warning/30 bg-warning/10 text-warning">
          <span aria-hidden className="text-lg">🎭</span>
        </div>
        <div className="min-w-0">
          <CardTitle className="text-base">{t("offers.rehearsalTitle")}</CardTitle>
          <CardDescription>{t("offers.rehearsalDescription")}</CardDescription>
        </div>
        {Object.keys(state.scores).length > 0 && (
                    <Hint side="left" label={t("chrome.resetHint")}>
<Button variant="ghost" size="icon-sm" className="ml-auto shrink-0" onClick={reset} aria-label={t("offers.rehearsalReset")} title={t("offers.rehearsalReset")}>
            <RotateCcw aria-hidden className="size-4" />
          </Button>
          </Hint>
        )}
      </CardHeader>
      <CardContent className="space-y-4">
        {done ? (
          <div className="space-y-4">
            <div role="status" className="rounded-xl border border-warning/30 bg-warning/10 px-4 py-3">
              <div className="flex flex-wrap items-baseline justify-between gap-3">
                <p className="text-sm font-semibold">{t("offers.rehearsalScoreLine", { total, max: MAX_REHEARSAL_SCORE })}</p>
                <p className="text-2xs uppercase tracking-widest text-muted-foreground">{t(VERDICT_KEY(band))}</p>
              </div>
              <p className="mt-2 text-sm leading-relaxed text-foreground/90">{t(`${VERDICT_KEY(band)}Detail`)}</p>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="rehearsal-keep">{t("offers.rehearsalKeepTitle")}</Label>
              <p className="text-2xs text-muted-foreground">{t("offers.rehearsalKeepDescription")}</p>
              <Textarea
                id="rehearsal-keep"
                value={state.sentence}
                onChange={setSentence}
                placeholder={t("offers.rehearsalKeepPlaceholder")}
                rows={2}
                maxLength={2000}
                className="text-sm leading-relaxed"
              />
              {state.sentence.trim() !== "" && (
                <p className="inline-flex items-center gap-1.5 text-2xs text-success">
                  <Check aria-hidden className="size-3" />
                  {t("offers.rehearsalKept")}
                </p>
              )}
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            <p className="text-2xs uppercase tracking-widest text-muted-foreground">
              {t("offers.rehearsalStep", { n: step + 1 })}
            </p>
            <p className="text-sm leading-relaxed">{t(`offers.rehearsalPush_${current?.id}`)}</p>
            <div role="radiogroup" aria-label={t(`offers.rehearsalPush_${current?.id}`)} className="flex flex-col gap-2">
              {current?.replies.map((reply) => {
                const active = picked === reply.id;
                const known = picked !== undefined;
                const score = scoreOf(current.id, reply.id);
                return (
                  <button
                    key={reply.id}
                    type="button"
                    role="radio"
                    aria-checked={active}
                    onClick={() => pick(current.id, reply.id)}
                    className={cn(
                      "rounded-lg border border-border/60 p-3 text-left text-sm transition-colors duration-150 focus-visible:ring-[3px] focus-visible:ring-primary/30",
                      active && "border-warning/40 bg-warning/10",
                      !active && "hover:border-border hover:bg-accent/30"
                    )}
                  >
                    {t(`offers.rehearsalReply_${current.id}_${reply.id}`)}
                    {known && active && (
                      <span className="mt-2 block text-2xs font-medium text-muted-foreground">
                        {score}/3 · {t(FEEDBACK_KEY(score))}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
            {picked && (
              <Button variant="ai" size="sm" onClick={advance} className="w-full">
                {isLast ? t("offers.rehearsalSeeVerdict") : t("offers.rehearsalNext")}
              </Button>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
