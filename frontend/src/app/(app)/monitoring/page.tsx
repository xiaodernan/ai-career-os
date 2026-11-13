"use client";

import * as React from "react";
import { Activity, AlertTriangle, Database, DollarSign, Gauge, Zap } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Progress } from "@/components/ui/progress";
import { ErrorState } from "@/components/common/error-state";
import { PageHeader } from "@/components/common/page-header";
import { BarChart } from "@/components/common/bar-chart";
import { NightlyHistory } from "@/components/monitoring/nightly-history";
import { ServiceEngines } from "@/components/monitoring/service-engines";
import { ServiceResilience } from "@/components/monitoring/service-resilience";
import { ServiceTopology } from "@/components/monitoring/service-topology";
import { useHealthReport, useAiSpendToday } from "@/lib/hooks/monitoring";
import type { AiSpendToday } from "@/lib/api/types";
import { useLocale } from "@/lib/i18n/locale-context";
import { formatNumber } from "@/lib/format";
import { healthVerdictWord } from "@/lib/status-words";

/** A 0–1 rate as a percent string. "No data" is an em dash, not a zero. */
function percent(value?: number): string {
  if (value == null || !Number.isFinite(value)) return "—";
  return `${Math.round(value * 100)}%`;
}

/**
 * The monitoring page (16.1): agent health, cost, and regression detection.
 * All metrics are deterministic, evidence-bound reads over the user's own data.
 */
export default function MonitoringPage() {
  const { t } = useLocale();
  const report = useHealthReport();
  const spend = useAiSpendToday();
  const data = report.data;
  const spendData = spend.data;

  return (
    <div className="space-y-6">
      <PageHeader
        frontDoor
        title={t("monitoring.title")}
        description={t("monitoring.description")}
        actions={
          <Button variant="outline" size="sm" onClick={() => { void report.refetch(); void spend.refetch(); }}>
            {t("common.refresh")}
          </Button>
        }
      />

      {report.isPending && (
        <div className="space-y-4">
          <Skeleton className="h-32 rounded-xl" />
          <Skeleton className="h-48 rounded-xl" />
        </div>
      )}

      {report.isError && (
        <ErrorState
          title={t("monitoring.loadFailed")}
          error={report.error}
          onRetry={() => void report.refetch()}
          retrying={report.isFetching}
        />
      )}

      {!report.isPending && !report.isError && data && (
        <>
          {/* Verdict */}
          <Card>
            <CardHeader>
              <CardTitle>{t("monitoring.healthVerdict")}</CardTitle>
              <CardDescription>{t("monitoring.verdictDescription")}</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-3">
                <Badge
                  variant={data.verdict === "healthy" ? "success" : data.verdict === "warn" ? "warning" : "destructive"}
                  className="text-sm"
                >
                  {healthVerdictWord(t, data.verdict ?? "unknown")}
                </Badge>
                <span className="text-sm text-muted-foreground">
                  {t("monitoring.runsAnalyzed", { count: data.totalRuns ?? 0 })}
                </span>
              </div>
            </CardContent>
          </Card>

          {/* Metrics */}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
            <MetricCard
              icon={<Activity className="size-4" aria-hidden />}
              label={t("monitoring.errorRate")}
              value={percent(data.errorRate)}
              tone={data.errorRate != null && data.errorRate > 0.1 ? "warning" : undefined}
            />
            <MetricCard
              icon={<DollarSign className="size-4" aria-hidden />}
              label={t("monitoring.totalCost")}
              value={`$${(data.totalCostUsd ?? 0).toFixed(2)}`}
            />
            <MetricCard
              icon={<Zap className="size-4" aria-hidden />}
              label={t("monitoring.totalTokens")}
              value={formatNumber(data.totalTokens ?? 0)}
            />
            <MetricCard
              icon={<Gauge className="size-4" aria-hidden />}
              label={t("monitoring.p95Latency")}
              value={`${formatNumber(data.p95LatencyMs ?? 0)}ms`}
            />
            <MetricCard
              icon={<Database className="size-4" aria-hidden />}
              label={t("monitoring.cacheHitRate")}
              value={percent(data.cacheHitRatio)}
              tone={data.cacheHitRatio != null && data.cacheHitRatio < 0.2 ? "warning" : undefined}
            />
            <MetricCard
              icon={<Database className="size-4" aria-hidden />}
              label={t("monitoring.cacheTokens")}
              value={formatNumber(data.totalCachedTokens ?? 0)}
            />
          </div>

          {/* Why the number looks the way it does, in the engine's own words: which
              calls the provider's prefix cache can fire on and which calls the
              exact-match cache replays. An operator who reads this cannot be
              confused by a low ratio on one-shot feature calls again. */}
          <Card>
            <CardHeader>
              <CardTitle>{t("monitoring.promptCache")}</CardTitle>
              <CardDescription>{t("monitoring.promptCacheDescription")}</CardDescription>
            </CardHeader>
          </Card>

          {/* Today's spend (21.x): the one number the user can act on, straight off
              the ledger the engine books every model call to. The bar is the reading,
              not a gate — nothing here refuses or throttles; `0` in the cap removes it. */}
          <SpendTodayCard
            spend={spendData}
            pending={spend.isPending}
            error={spend.isError ? spend.error : null}
            onRetry={() => void spend.refetch()}
          />

          {/* The latency pair, as a chart: the p50 is the experience and the
              p95 is the tail, and one number for each says less than the two
              side by side. */}
          {typeof data.p50LatencyMs === "number" && typeof data.p95LatencyMs === "number" && (
            <Card>
              <CardHeader>
                <CardTitle>{t("monitoring.latency")}</CardTitle>
                <CardDescription>
                  {t("monitoring.latencyDescription")}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <BarChart
                  data={[
                    { label: t("monitoring.p50"), value: data.p50LatencyMs!, tone: "primary" },
                    { label: t("monitoring.p95"), value: data.p95LatencyMs!, tone: "warning" },
                  ]}
                  valueFormat={(v) => `${formatNumber(v)}ms`}
                />
              </CardContent>
            </Card>
          )}

          {/* Alerts */}
          {(data.alerts?.length ?? 0) > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>{t("monitoring.alerts")}</CardTitle>
                <CardDescription>{t("monitoring.alertsDescription")}</CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2">
                  {data.alerts!.map((alert, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm">
                      <AlertTriangle className="mt-0.5 size-4 shrink-0 text-warning" aria-hidden />
                      {alert}
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}

          {/* Regressions */}
          {(data.regressions?.length ?? 0) > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>{t("monitoring.regressions")}</CardTitle>
                <CardDescription>{t("monitoring.regressionsDescription")}</CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2">
                  {data.regressions!.map((reg, i) => (
                    <li key={i} className="flex items-center justify-between rounded-lg border border-border/50 p-3">
                      <div>
                        <p className="text-sm font-medium">{reg.metric}</p>
                        <p className="text-xs text-muted-foreground">
                          {reg.direction} · {reg.severity}
                        </p>
                      </div>
                      <Badge variant="destructive">{reg.severity}</Badge>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}
        </>
      )}

      {/* The deployment's own history sits outside the agent-health conditional: it is
          read from its own endpoint and answers its own states, so a failed health
          report does not hide the nights that passed. */}
      <NightlyHistory />

      {/* The deployment's fleet, read from the discovery answer the load balancer
          consumes rather than from a second inventory. */}
      <ServiceTopology />

      {/* Spring Cloud circuit breaker states for the ai-service bridge (Epic 105). */}
      <ServiceResilience />

      {/* The engine fleet the backend can call right now (Epic 108.23). */}
      <ServiceEngines />
    </div>
  );
}

function SpendTodayCard({
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

function MetricCard({
  icon,
  label,
  value,
  tone,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  tone?: "warning";
}) {
  return (
    <Card>
      <CardHeader>
        <CardDescription className="flex items-center gap-1.5">
          <span className="text-muted-foreground [&_svg]:size-3.5">{icon}</span>
          {label}
        </CardDescription>
        <CardTitle
          className={`text-2xl font-semibold tabular-nums ${tone === "warning" ? "text-warning" : ""}`}
        >
          {value}
        </CardTitle>
      </CardHeader>
    </Card>
  );
}
