"use client";

import * as React from "react";
import { Activity, AlertTriangle, DollarSign, Gauge, Zap } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { BarChart } from "@/components/common/bar-chart";
import { useHealthReport } from "@/lib/hooks/monitoring";
import { useLocale } from "@/lib/i18n/locale-context";
import { formatNumber } from "@/lib/format";
import type { HealthReport } from "@/lib/api/types";

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
  const data = report.data;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{t("monitoring.title")}</h1>
          <p className="text-sm text-muted-foreground">{t("monitoring.description")}</p>
        </div>
        <Button variant="outline" size="sm" onClick={() => void report.refetch()}>
          Refresh
        </Button>
      </div>

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
              <CardDescription>Overall agent health assessment.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-3">
                <Badge
                  variant={data.verdict === "healthy" ? "success" : data.verdict === "warn" ? "warning" : "destructive"}
                  className="text-sm"
                >
                  {data.verdict ?? "unknown"}
                </Badge>
                <span className="text-sm text-muted-foreground">
                  {data.totalRuns ?? 0} runs analyzed
                </span>
              </div>
            </CardContent>
          </Card>

          {/* Metrics */}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
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
          </div>

          {/* The latency pair, as a chart: the p50 is the experience and the
              p95 is the tail, and one number for each says less than the two
              side by side. */}
          {typeof data.p50LatencyMs === "number" && typeof data.p95LatencyMs === "number" && (
            <Card>
              <CardHeader>
                <CardTitle>Latency</CardTitle>
                <CardDescription>
                  The median call and the slow tail, on one scale.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <BarChart
                  data={[
                    { label: "p50 (median)", value: data.p50LatencyMs!, tone: "primary" },
                    { label: "p95 (tail)", value: data.p95LatencyMs!, tone: "warning" },
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
    </div>
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
