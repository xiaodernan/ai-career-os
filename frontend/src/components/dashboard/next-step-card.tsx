"use client";

import * as React from "react";
import { Sparkles } from "lucide-react";

import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Hint } from "@/components/ui/hint";
import { SectionHeading } from "@/components/common/export-buttons";
import { useLocale } from "@/lib/i18n/locale-context";
import { useNextStep } from "@/lib/hooks/assistant";

/**
 * Epic 331 — the assistant's one proactive first step.
 *
 * The dashboard owns the numbers; this card is the one sentence the reader can act on
 * before anything else. It never runs for free: a click starts it, the server alone
 * sees the workspace, and a silent assistant renders nothing rather than a chant.
 */
export function NextStepCard() {
  const { t, locale } = useLocale();
  const nextStep = useNextStep();
  const step = nextStep.data?.step ?? null;

  return (
    <Card>
      <CardHeader className="pb-3">
        <SectionHeading
          eyebrow={t("eyebrows.nextStep")}
          icon={<Sparkles className="size-4" aria-hidden />}
          title={t("dashboard.nextStepTitle")}
          description={t("dashboard.nextStepDescription")}
        />
      </CardHeader>
      <CardContent>
        {step ? (
          <p className="text-sm leading-relaxed text-foreground">{step}</p>
        ) : (
          <p className="text-sm text-muted-foreground">{t("dashboard.nextStepEmpty")}</p>
        )}
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <Hint label={t("dashboard.nextStepHint")}>
            <Button
              variant="ai"
              size="sm"
              loading={nextStep.isPending}
              onClick={() => nextStep.mutate({ locale })}
            >
              {step ? t("dashboard.nextStepAgain") : t("dashboard.nextStepRun")}
            </Button>
          </Hint>
          {nextStep.isPending ? (
            <span className="text-xs text-muted-foreground">{t("dashboard.nextStepPending")}</span>
          ) : null}
        </div>
        {nextStep.isError ? (
          <p className="mt-2 text-sm text-destructive">{t("dashboard.nextStepError")}</p>
        ) : null}
      </CardContent>
    </Card>
  );
}
