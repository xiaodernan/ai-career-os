"use client";

/**
 * The near-miss (Epic 270) — the role that almost was.
 *
 * Every reader has one close call worth keeping: the final round that went elsewhere,
 * the offer that barely bent to a competing hand. The not-yet letter holds what the
 * no felt like; this shelf holds what it taught. Five pieces make one complete near-miss —
 * role, company, ask-again, the lesson, what changed since. Nothing is sent anywhere;
 * local-only, carried in the reader's browser like every other keepsake.
 */

import * as React from "react";
import { Archive, RotateCcw } from "lucide-react";
import { cn } from "@/lib/utils";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Hint } from "@/components/ui/hint";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useLocale } from "@/lib/i18n/locale-context";
import {
  SLOT_COUNT,
  blankState,
  filledSlots,
  isSealed,
  readNearMiss,
  writeNearMiss,
  type NearMissState,
} from "@/lib/nearmiss";

export function NearMissCard() {
  const { t } = useLocale();
  const [state, setState] = React.useState<NearMissState>(() =>
    blankState(),
  );
  const [loaded, setLoaded] = React.useState(false);

  React.useEffect(() => {
    setState(readNearMiss(typeof window === "undefined" ? null : window.localStorage));
    setLoaded(true);
  }, []);

  const seal = (patch: Partial<NearMissState>) => {
    setState((current) => {
      const next = { ...current, ...patch, keptAt: new Date().toISOString() };
      writeNearMiss(next);
      return next;
    });
  };

  const reset = () => {
    const blank = blankState();
    setState(blank);
    writeNearMiss(blank);
  };

  const filled = loaded ? filledSlots(state).length : 0;
  const sealed = loaded && isSealed(state);

  return (
    <Card
      data-testid="near-miss-card"
      className="overflow-hidden border-border/70 bg-gradient-to-br from-muted/40 via-card to-card shadow-card print:break-inside-avoid"
    >
      <CardHeader className="flex flex-row items-start gap-4 space-y-0">
        <div className="flex size-10 shrink-0 items-center justify-center rounded-xl border border-border/70 bg-muted/60 text-muted-foreground">
          <Archive aria-hidden className="size-5" />
        </div>
        <div className="min-w-0 flex-1">
          <CardTitle className="text-base">{t("replies.nearTitle")}</CardTitle>
          <CardDescription>{t("replies.nearDescription")}</CardDescription>
        </div>
        {loaded && (state.role || state.learned || state.changed) && (
          <Hint side="left" label={t("chrome.resetHint")}>
            <Button variant="ghost" size="icon-sm" onClick={reset} aria-label={t("replies.nearReset")} title={t("replies.nearReset")}>
              <RotateCcw aria-hidden className="size-4" />
            </Button>
          </Hint>
        )}
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-[1fr_1fr]">
          <div className="space-y-1">
            <Label htmlFor="near-role">{t("replies.nearRole")}</Label>
            <Input
              id="near-role"
              spellCheck="false"
              placeholder={t("replies.nearRolePlaceholder")}
              value={loaded ? state.role : ""}
              onChange={(event) => seal({ role: event.target.value })}
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="near-company">{t("replies.nearCompany")}</Label>
            <Input
              id="near-company"
              spellCheck="false"
              placeholder={t("replies.nearCompanyPlaceholder")}
              value={loaded ? state.company : ""}
              onChange={(event) => seal({ company: event.target.value })}
            />
          </div>
        </div>

        <fieldset className="space-y-1.5">
          <legend className="text-sm font-medium">{t("replies.nearAgain")}</legend>
          <div className="flex gap-2" role="group" aria-label={t("replies.nearAgain")}>
            {([true, false] as const).map((choice) => (
              <Button
                key={String(choice)}
                type="button"
                variant={state.again === choice ? "primary" : "outline"}
                aria-pressed={state.again === choice}
                className="h-8 text-2xs"
                onClick={() => seal({ again: state.again === choice ? null : choice })}
              >
                {t(choice ? "replies.nearAgainYes" : "replies.nearAgainNo")}
              </Button>
            ))}
          </div>
        </fieldset>

        <div className="space-y-1">
          <Label htmlFor="near-learned">{t("replies.nearLearned")}</Label>
          <Textarea
            id="near-learned"
            rows={2}
            spellCheck="false"
            placeholder={t("replies.nearLearnedPlaceholder")}
            value={loaded ? state.learned : ""}
            onChange={(event) => seal({ learned: event.target.value })}
          />
        </div>

        <div className="space-y-1">
          <Label htmlFor="near-changed">{t("replies.nearChanged")}</Label>
          <Textarea
            id="near-changed"
            rows={2}
            spellCheck="false"
            placeholder={t("replies.nearChangedPlaceholder")}
            value={loaded ? state.changed : ""}
            onChange={(event) => seal({ changed: event.target.value })}
          />
        </div>

        <div className="flex items-center justify-between gap-3 text-xs tabular-nums text-muted-foreground">
          <span>{sealed ? t("replies.nearSealed") : t("replies.nearProgress", { done: filled, total: SLOT_COUNT })}</span>
          <div
            className="h-1.5 w-36 overflow-hidden rounded-full bg-muted"
            role="progressbar"
            aria-valuemin={0}
            aria-valuemax={SLOT_COUNT}
            aria-valuenow={filled}
            aria-label={t("replies.nearProgress", { done: filled, total: SLOT_COUNT })}
          >
            <div
              className={cn("h-full rounded-full bg-primary transition-[width]", sealed && "bg-success")}
              style={{ width: `${Math.round((filled / SLOT_COUNT) * 100)}%` }}
            />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
