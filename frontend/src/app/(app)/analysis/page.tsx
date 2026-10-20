"use client";

import * as React from "react";
import { Activity, AlertTriangle, BarChart3, Clock, TrendingUp } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { BarChart, ShareChart } from "@/components/common/bar-chart";
import { LoadingListSkeleton } from "@/components/common/loading-skeletons";
import { SectionBoundary } from "@/components/common/query-boundary";
import { useInsightDigest, usePipelineFunnel, useResponseRate } from "@/lib/hooks/analytics";
import { useLocale } from "@/lib/i18n/locale-context";
import { formatNumber } from "@/lib/format";
import type { InsightDigest } from "@/lib/api/types";

/** A 0–1 rate as a percent string. "No data" is an em dash, not a zero. */
function percent(value?: number): string {
  if (value == null || !Number.isFinite(value)) return "—";
  return `${Math.round(value * 100)}%`;
}

/**
 * The analysis page (15.3): a weekly insight digest composed by the ai-service's
 * analytics engine. Shows stalled applications, the live stage mix, and headline
 * rates — all deterministic, evidence-bound metrics over the user's own data.
 */
export default function AnalysisPage() {
  const { t } = useLocale();
  const digest = useInsightDigest();
  const funnel = usePipelineFunnel();
  const rates = useResponseRate();
  const data = digest.data;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{t("analysis.title")}</h1>
          <p className="text-sm text-muted-foreground">{t("analysis.description")}</p>
        </div>
        <Button variant="outline" size="sm" onClick={() => void digest.refetch()}>
          Refresh
        </Button>
      </div>

      {digest.isPending && (
        <div className="space-y-4">
          <Skeleton className="h-32 rounded-xl" />
          <Skeleton className="h-48 rounded-xl" />
          <Skeleton className="h-40 rounded-xl" />
        </div>
      )}

      {digest.isError && (
        <ErrorState
          title="Analysis failed to load"
          error={digest.error}
          onRetry={() => void digest.refetch()}
          retrying={digest.isFetching}
        />
      )}

      {!digest.isPending && !digest.isError && data && (
        <>
          {/* Headline metrics */}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <MetricCard
              icon={<BarChart3 className="size-4" aria-hidden />}
              label={t("analysis.totalApplications")}
              value={formatNumber(data.totalApplications)}
            />
            <MetricCard
              icon={<Activity className="size-4" aria-hidden />}
              label={t("analysis.activePipeline")}
              value={formatNumber(data.activePipeline)}
            />
            <MetricCard
              icon={<TrendingUp className="size-4" aria-hidden />}
              label={t("analysis.responseRate")}
              value={percent(data.responseRate)}
            />
            <MetricCard
              icon={<AlertTriangle className="size-4" aria-hidden />}
              label={t("analysis.stalled")}
              value={formatNumber(data.stalledCount ?? 0)}
              tone={(data.stalledCount ?? 0) > 0 ? "warning" : undefined}
            />
          </div>

          {/* Stage mix */}
          <Card>
            <CardHeader>
              <CardTitle>{t("analysis.stageMix")}</CardTitle>
              <CardDescription>Applications at each pipeline stage.</CardDescription>
            </CardHeader>
            <CardContent>
              {Object.keys(data.stageCounts ?? {}).length > 0 ? (
                <ShareChart
                  data={Object.entries(data.stageCounts ?? {}).map(([stage, count]) => ({
                    label: stage.replace(/_/g, " "),
                    value: count,
                    detail: `${count}`,
                    tone:
                      stage === "offer"
                        ? "success"
                        : stage === "rejected"
                          ? "destructive"
                          : "primary",
                  }))}
                />
              ) : (
                <p className="text-sm text-muted-foreground">
                  No applications have reached a stage yet.
                </p>
              )}
            </CardContent>
          </Card>

          {/* 15.1 — the funnel: where the pipeline leaks */}
          <Card>
            <CardHeader>
              <CardTitle>{t("analysis.funnel")}</CardTitle>
              <CardDescription>{t("analysis.funnelDescription")}</CardDescription>
            </CardHeader>
            <CardContent>
              {(funnel.data?.pipeline?.length ?? 0) > 0 ? (
                <BarChart
                  data={funnel.data!.pipeline!.map((stage, i) => ({
                    label: stage.stage?.replace(/_/g, " ") ?? `Stage ${i + 1}`,
                    value: stage.count ?? 0,
                    detail: `${percent(stage.conversionFromApplied)} of applied`,
                    // The last stage is the one the search is for, so it reads
                    // green; the ones before it are the funnel's own colour.
                    tone:
                      stage.stage === "offer"
                        ? "success"
                        : stage.stage === "final_round"
                          ? "primary"
                          : "muted",
                  }))}
                />
              ) : funnel.isPending ? (
                <LoadingListSkeleton rows={3} />
              ) : (
                <EmptyState
                  icon={<BarChart3 aria-hidden />}
                  title={t("analysis.noFunnel")}
                  description={t("analysis.noFunnelDescription")}
                />
              )}
            </CardContent>
          </Card>

          {/* 15.2 — the rates */}
          {rates.data && (
            <Card>
              <CardHeader>
                <CardTitle>{t("analysis.responseRates")}</CardTitle>
                <CardDescription>{t("analysis.responseRatesDescription")}</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-3 gap-3 text-center">
                  <RateCell label={t("analysis.reply")} value={rates.data.responseRate} />
                  <RateCell label={t("analysis.interview")} value={rates.data.interviewRate} />
                  <RateCell label={t("analysis.offer")} value={rates.data.offerRate} />
                </div>
                {(rates.data.appliedCount ?? 0) > 0 && (
                  <p className="mt-3 text-xs text-muted-foreground">
                    {formatNumber(rates.data.respondedCount ?? 0)} of{" "}
                    {formatNumber(rates.data.appliedCount ?? 0)} submitted applications
                    got a reply.
                  </p>
                )}
              </CardContent>
            </Card>
          )}

          {/* Stalled applications */}
          <Card>
            <CardHeader>
              <CardTitle>{t("analysis.stalledApplications")}</CardTitle>
              <CardDescription>
                Applications with no movement past {data.windowDays ?? 14} days.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {(data.stalled?.length ?? 0) > 0 ? (
                <ul className="space-y-2">
                  {data.stalled!.slice(0, 5).map((s) => (
                    <li
                      key={s.id}
                      className="flex items-center justify-between rounded-lg border border-border/50 p-3"
                    >
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium">{s.title}</p>
                        <p className="text-xs text-muted-foreground">
                          {s.company ?? "—"} · {s.status}
                        </p>
                      </div>
                      <Badge variant="warning" className="shrink-0">
                        {s.daysSinceLastActivity}d
                      </Badge>
                    </li>
                  ))}
                </ul>
              ) : (
                <EmptyState
                  icon={<Clock aria-hidden />}
                  title={t("analysis.noStalled")}
                  description={t("analysis.noStalledDescription")}
                />
              )}
            </CardContent>
          </Card>

          {/* Signals */}
          {(data.signals?.length ?? 0) > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>{t("analysis.insights")}</CardTitle>
                <CardDescription>What the data says about your pipeline.</CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2">
                  {data.signals!.map((signal, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm">
                      <span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-primary" aria-hidden />
                      {signal}
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

/** One rate, as a percent. "No data" is an em dash, not a zero. */
function RateCell({ label, value }: { label: string; value?: number }) {
  return (
    <div className="rounded-lg border border-border/50 p-3">
      <p className="text-lg font-semibold tabular-nums">{percent(value)}</p>
      <p className="text-xs text-muted-foreground">{label}</p>
    </div>
  );
}
