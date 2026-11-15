"use client";

import * as React from "react";
import { Check, Coffee, RotateCcw } from "lucide-react";
import { cn } from "@/lib/utils";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { useLocale } from "@/lib/i18n/locale-context";
import {
  MAX_COFFEE_SCORE,
  COFFEE_MOMENTS,
  clearCoffeeChat,
  coffeeAnswered,
  coffeeScoreOf,
  coffeeTotalScore,
  coffeeVerdictBand,
  loadCoffeeChat,
  saveCoffeeChat,
  type CoffeeChatState,
} from "@/lib/networking/coffee-chat";

/**
 * The first coffee (Epic 230) — the conversation before the referral.
 *
 * The registry knows who the reader knows; this room rehearses the fifteen
 * minutes before either one of them names the ask. Three moments — the
 * ask, the middle, the close — three replies each, a verdict at nine.
 * Nothing here is advice; it is the shape the chat actually takes,
 * rehearsed where fumbles are free. The chosen sentence lives in this
 * browser only, like the ledger and the debriefs.
 */
const FEEDBACK_KEY = (score: number): string =>
  score >= 3
    ? "networking.coffeeFeedbackSpecific"
    : score >= 2
      ? "networking.coffeeFeedbackWarm"
      : score >= 1
        ? "networking.coffeeFeedbackSafe"
        : "networking.coffeeFeedbackBurdens";

const VERDICT_KEY = (band: string): string =>
  `networking.coffeeVerdict${band.charAt(0).toUpperCase()}${band.slice(1)}`;

export function CoffeeChatCard() {
  const { t } = useLocale();
  const [state, setState] = React.useState<CoffeeChatState>(() =>
    loadCoffeeChat(typeof window === "undefined" ? null : window.localStorage)
  );
  const [revealed, setRevealed] = React.useState<Record<string, boolean>>({});
  const [step, setStep] = React.useState(0);

  const done = coffeeAnswered(state);
  const current = COFFEE_MOMENTS[step];
  const picked = current ? state.scores[current.id] : undefined;
  const total = coffeeTotalScore(state);
  const band = coffeeVerdictBand(total);
  const isLast = step === COFFEE_MOMENTS.length - 1;

  const pick = (momentId: string, replyId: string) => {
    const nextScores = { ...state.scores, [momentId]: replyId };
    setState((prev) => ({ ...prev, scores: nextScores }));
    setRevealed((prev) => ({ ...prev, [momentId]: true }));
    saveCoffeeChat({ scores: nextScores, sentence: state.sentence });
  };

  const setSentence = (event: React.ChangeEvent<HTMLTextAreaElement>) => {
    setState((prev) => {
      const next = { ...prev, sentence: event.target.value };
      saveCoffeeChat(next);
      return next;
    });
  };

  const reset = () => {
    clearCoffeeChat();
    setState({ scores: {}, sentence: "" });
    setRevealed({});
    setStep(0);
  };

  const advance = () => setStep((currentStep) => Math.min(currentStep + 1, COFFEE_MOMENTS.length - 1));

  return (
    <Card
      data-testid="coffee-chat-card"
      className="overflow-hidden border-success/25 bg-gradient-to-br from-success/5 via-card to-card shadow-card print:break-inside-avoid"
    >
      <CardHeader className="flex flex-row items-start gap-4 space-y-0">
        <div className="flex size-10 shrink-0 items-center justify-center rounded-xl border border-success/30 bg-success/10 text-success">
          <Coffee aria-hidden className="size-5" />
        </div>
        <div className="min-w-0">
          <CardTitle className="text-base">{t("networking.coffeeTitle")}</CardTitle>
          <CardDescription>{t("networking.coffeeDescription")}</CardDescription>
        </div>
        {Object.keys(state.scores).length > 0 && (
          <Button variant="ghost" size="icon-sm" className="ml-auto shrink-0" onClick={reset} aria-label={t("networking.coffeeReset")}>
            <RotateCcw aria-hidden className="size-4" />
          </Button>
        )}
      </CardHeader>
      <CardContent className="space-y-4">
        {done ? (
          <div className="space-y-4">
            <div role="status" className="rounded-xl border border-success/30 bg-success/10 px-4 py-3">
              <div className="flex flex-wrap items-baseline justify-between gap-3">
                <p className="text-sm font-semibold">{t("networking.coffeeScoreLine", { total, max: MAX_COFFEE_SCORE })}</p>
                <p className="text-2xs uppercase tracking-widest text-muted-foreground">{t(VERDICT_KEY(band))}</p>
              </div>
              <p className="mt-2 text-sm leading-relaxed text-foreground/90">{t(`${VERDICT_KEY(band)}Detail`)}</p>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="coffee-keep">{t("networking.coffeeKeepTitle")}</Label>
              <p className="text-2xs text-muted-foreground">{t("networking.coffeeKeepDescription")}</p>
              <Textarea
                id="coffee-keep"
                value={state.sentence}
                onChange={setSentence}
                placeholder={t("networking.coffeeKeepPlaceholder")}
                rows={2}
                maxLength={2000}
                className="text-sm leading-relaxed"
              />
              {state.sentence.trim() !== "" && (
                <p className="inline-flex items-center gap-1.5 text-2xs text-success">
                  <Check aria-hidden className="size-3" />
                  {t("networking.coffeeKept")}
                </p>
              )}
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            <p className="text-2xs uppercase tracking-widest text-muted-foreground">
              {t("networking.coffeeStep", { n: step + 1 })}
            </p>
            <p className="text-sm leading-relaxed">{t(`networking.coffeePush_${current?.id}`)}</p>
            <div role="radiogroup" aria-label={t(`networking.coffeePush_${current?.id}`)} className="flex flex-col gap-2">
              {current?.replies.map((reply) => {
                const active = picked === reply.id;
                const known = picked !== undefined;
                const score = coffeeScoreOf(current.id, reply.id);
                return (
                  <button
                    key={reply.id}
                    type="button"
                    role="radio"
                    aria-checked={active}
                    onClick={() => pick(current.id, reply.id)}
                    className={cn(
                      "rounded-lg border border-border/60 p-3 text-left text-sm transition-colors duration-150 focus-visible:ring-[3px] focus-visible:ring-success/30",
                      active && "border-success/40 bg-success/10",
                      !active && "hover:border-border hover:bg-accent/30"
                    )}
                  >
                    {t(`networking.coffeeReply_${current.id}_${reply.id}`)}
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
                {isLast ? t("networking.coffeeSeeVerdict") : t("networking.coffeeNext")}
              </Button>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
