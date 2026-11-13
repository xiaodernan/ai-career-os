"use client";

import * as React from "react";
import { DollarSign } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Progress } from "@/components/ui/progress";
import { ErrorState } from "@/components/common/error-state";
import type { AiSpendToday } from "@/lib/api/types";
import { formatNumber } from "@/lib/format";
import { useLocale } from "@/lib/i18n/locale-context";

/**
 * The day's AI spend card (21.x): what today cost the reader, the cap that keeps
 * them company, and the three sub-readings that explain the number.
 *
 * The cap is the dashboard's watchful scale, never a gate — nothing in this card
 * refuses, throttles or blocks; `0` removes the bar entirely.
 */

function percent(value?: number): string {
  if (value == null || !Number.isFinite(value)) return "—";
  return `${Math.round(value * 100)}%`;
}

export function SpendTodayCard({
  spend,
  pending,
  error,
  onRetry,
}: {
  spend?: AiSpendToday;
  pending: boolean;
  error: unknown;
  onRetry: () => void;
}) {
  const { t } = useLocale();

  if (pending) {
    return <Skeleton className="h-40 rounded-xl" aria-label={t("monitoring.spendToday")} />;
  }
  if (error) {
    return (
      <ErrorState
        title={t("monitoring.spendTodayFailed")}
        error={error}
        onRetry={onRetry}
      />
    );
  }
  if (!spend) {
    return null;
  }
  const cap = spend.capUsd ?? 0;
  const ratio = cap > 0 ? Math.min(1, (spend.costUsd ?? 0) / cap) : 0;
  const barPct = Math.round(ratio * 100);
  const tone = spend.capExceeded ? "destructive" : ratio >= 0.8 ? "warning" : "primary";
  const indicator =
    tone === "destructive"
      ? "bg-destructive [&_[data-slot=progress-indicator]]:bg-destructive"
      : tone === "warning"
        ? "bg-warning [&_[data-slot=progress-indicator]]:bg-warning"
        : "";
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between gap-3">
          <div>
            <CardTitle className="flex items-center gap-2">
              <DollarSign className="size-4 text-muted-foreground" aria-hidden />
              {t("monitoring.spendToday")}
            </CardTitle>
            <CardDescription>{t("monitoring.spendTodayDescription")}</CardDescription>
          </div>
          <Badge variant={spend.capExceeded ? "destructive" : "outline"} className="shrink-0">
            {t("monitoring.spendTodayCalls", { count: formatNumber(spend.calls ?? 0) })}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex flex-wrap items-baseline justify-between gap-3">
          <span className="text-3xl font-semibold tabular-nums">
            ${(spend.costUsd ?? 0).toFixed(4)}
          </span>
          <span className="text-xs text-muted-foreground">
            {spend.capEnabled && cap > 0
              ? t("monitoring.spendTodayOfCap", { cap: cap.toFixed(2) })
              : t("monitoring.spendTodayNoCap")}
          </span>
        </div>
        {spend.capEnabled && cap > 0 ? (
          <Progress
            value={barPct}
            aria-label={t("monitoring.spendTodayProgress")}
            className={indicator}
          />
        ) : null}
        <div className="grid gap-2 text-xs text-muted-foreground sm:grid-cols-3">
          <span>{formatNumber(spend.inputTokens ?? 0)} {t("monitoring.spendTodayInput")}</span>
          <span>{formatNumber(spend.cachedTokens ?? 0)} {t("monitoring.spendTodayCached")}</span>
          <span>{percent(spend.cacheHitRatio)} {t("monitoring.cacheHitRate")}</span>
        </div>
      </CardContent>
    </Card>
  );
}
