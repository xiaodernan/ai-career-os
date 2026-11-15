"use client";

import * as React from "react";
import Link from "next/link";
import { ArrowRight, Check, RotateCcw, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Hint } from "@/components/ui/hint";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { useLocale } from "@/lib/i18n/locale-context";
import {
  FIRST_WEEK_SCENES,
  FIRST_WEEK_SCENE_COUNT,
  MAX_FIRST_WEEK_SCORE,
  firstWeekAnswered,
  firstWeekPoints,
  firstWeekTotal,
  firstWeekVerdict,
  loadFirstWeek,
  saveFirstWeek,
  type FirstWeekState,
} from "@/lib/playbook/first-week";

/**
 * Chapter zero — the first week, playable (Epic 233).
 *
 * The manual teaches the loop in prose; this is the same loop rehearsed with
 * a finger before the keyboard sees it. Six scenes, three forks each, one
 * honest verdict at the end. Nothing here registers you anywhere — the
 * choices stay in this browser, and finishing it registers nothing.
 */
const VERDICT_KEY = (band: string): string =>
  `playbook.firstweekVerdict${band.charAt(0).toUpperCase()}${band.slice(1)}`;

export function FirstWeekGame() {
  const { t } = useLocale();
  const [initial] = React.useState<FirstWeekState>(() =>
    loadFirstWeek(typeof window === "undefined" ? null : window.localStorage)
  );
  const firstUnanswered = (() => {
    const found = FIRST_WEEK_SCENES.findIndex((scene) => !(scene.id in initial.choices));
    return found === -1 ? FIRST_WEEK_SCENE_COUNT - 1 : found;
  })();
  const [state, setState] = React.useState<FirstWeekState>(initial);
  const [step, setStep] = React.useState(firstUnanswered);
  const [picked, setPicked] = React.useState<string | null>(
    initial.choices[FIRST_WEEK_SCENES[firstUnanswered].id] ?? null
  );

  const scene = FIRST_WEEK_SCENES[step];
  const done = firstWeekAnswered(state);
  const total = firstWeekTotal(state);
  const band = firstWeekVerdict(total);

  const pick = (sceneId: string, choiceId: string) => {
    const next = { choices: { ...state.choices, [sceneId]: choiceId }, sentence: state.sentence };
    setState(next);
    setPicked(choiceId);
    saveFirstWeek(next);
  };

  const setSentence = (event: React.ChangeEvent<HTMLTextAreaElement>) => {
    setState((prev) => {
      const next = { ...prev, sentence: event.target.value };
      saveFirstWeek(next);
      return next;
    });
  };

  const advance = () => {
    setPicked(null);
    setStep((s) => Math.min(s + 1, FIRST_WEEK_SCENE_COUNT - 1));
  };

  const replay = () => {
    const cleared = { choices: {}, sentence: "" };
    setState(cleared);
    setPicked(null);
    setStep(0);
    saveFirstWeek(cleared);
  };

  return (
    <Card
      data-testid="first-week-game"
      className="overflow-hidden border-primary/20 bg-gradient-to-br from-primary/[0.07] via-card to-card shadow-card print:break-inside-avoid"
    >
      <CardHeader className="flex flex-row items-start gap-4 space-y-0">
        <div className="flex size-10 shrink-0 items-center justify-center rounded-xl border border-primary/25 bg-primary/10 text-primary">
          <Sparkles aria-hidden className="size-5" />
        </div>
        <div className="min-w-0">
          <CardTitle className="text-base">{t("playbook.firstweekTitle")}</CardTitle>
          <CardDescription>{t("playbook.firstweekIntro")}</CardDescription>
        </div>
        {Object.keys(state.choices).length > 0 && (
                    <Hint side="left" label={t("chrome.resetHint")}>
<Button variant="ghost" size="icon-sm" className="ml-auto shrink-0" onClick={replay} aria-label={t("playbook.firstweekReplay")}>
            <RotateCcw aria-hidden className="size-4" />
          </Button>
          </Hint>
        )}
      </CardHeader>
      <CardContent className="space-y-4">
        {done ? (
          <div className="space-y-4">
            <div role="status" className="rounded-xl border border-primary/25 bg-primary/[0.06] px-4 py-3">
              <div className="flex flex-wrap items-baseline justify-between gap-3">
                <p className="text-sm font-semibold">{t("playbook.firstweekScoreLine", { total, max: MAX_FIRST_WEEK_SCORE })}</p>
                <p className="text-2xs uppercase tracking-widest text-muted-foreground">{t(VERDICT_KEY(band))}</p>
              </div>
              <p className="mt-2 text-sm leading-relaxed text-foreground/90">{t(`${VERDICT_KEY(band)}Detail`)}</p>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="firstweek-keep">{t("playbook.firstweekKeepTitle")}</Label>
              <p className="text-2xs text-muted-foreground">{t("playbook.firstweekKeepDescription")}</p>
              <Textarea
                id="firstweek-keep"
                value={state.sentence}
                onChange={setSentence}
                placeholder={t("playbook.firstweekKeepPlaceholder")}
                rows={2}
                maxLength={1000}
                className="text-sm leading-relaxed"
              />
              {state.sentence.trim() !== "" && (
                <p className="inline-flex items-center gap-1.5 text-2xs text-success">
                  <Check aria-hidden className="size-3" />
                  {t("playbook.firstweekKept")}
                </p>
              )}
            </div>
            <Button variant="ai" size="sm" asChild>
              <Link href="/register">
                {t("playbook.firstweekCta")}
                <ArrowRight aria-hidden className="size-4" />
              </Link>
            </Button>
          </div>
        ) : scene ? (
          <div className="space-y-3">
            <p className="text-2xs uppercase tracking-widest text-muted-foreground">
              {t("playbook.firstweekStep", { n: step + 1, total: FIRST_WEEK_SCENE_COUNT })}
            </p>
            <p className="text-sm leading-relaxed">{t(`playbook.firstweekScene_${scene.id}`)}</p>
            <div role="radiogroup" aria-label={t(`playbook.firstweekScene_${scene.id}`)} className="flex flex-col gap-2">
              {scene.choices.map((choice) => {
                const active = picked === choice.id || state.choices[scene.id] === choice.id;
                const known = picked !== null || state.choices[scene.id] !== undefined;
                const points = firstWeekPoints(scene.id, choice.id);
                return (
                  <button
                    key={choice.id}
                    type="button"
                    role="radio"
                    aria-checked={active}
                    disabled={picked !== null}
                    onClick={() => pick(scene.id, choice.id)}
                    className={cn(
                      "rounded-lg border border-border/60 p-3 text-left text-sm transition-colors duration-150 focus-visible:ring-[3px] focus-visible:ring-primary/30",
                      active && "border-primary/40 bg-primary/10",
                      !active && "hover:border-border hover:bg-accent/30",
                      picked !== null && !active && "opacity-60"
                    )}
                  >
                    {t(`playbook.firstweekChoice_${scene.id}_${choice.id}`)}
                    {known && active && (
                      <span className="mt-2 block text-2xs font-medium text-muted-foreground">
                        +{points} · {t(`playbook.firstweekReact_${points}`)}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
            {picked && (
              <Button variant="ai" size="sm" onClick={advance} className="w-full">
                {step === FIRST_WEEK_SCENE_COUNT - 1 ? t("playbook.firstweekSeeVerdict") : t("playbook.firstweekNext")}
              </Button>
            )}
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
