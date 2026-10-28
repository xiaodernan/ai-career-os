"use client";

import * as React from "react";
import { Activity, AlertTriangle, BarChart3, CalendarDays, Clock, TrendingUp } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { BarChart, ShareChart } from "@/components/common/bar-chart";
import { LoadingListSkeleton } from "@/components/common/loading-skeletons";
import {
  useComposeWeeklyDigest,
  useInsightDigest,
  usePipelineFunnel,
  useResponseRate,
  useWeeklyDigests,
} from "@/lib/hooks/analytics";
import { useLocale } from "@/lib/i18n/locale-context";
import { stageLabel } from "@/lib/pipeline";
import { formatDateOnly, formatNumber, relativeTime } from "@/lib/format";
import type { WeeklyDigest } from "@/lib/api/types";

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
  const { t, locale } = useLocale();
  // The engine's signals are sentences, so the request carries the reader's
  // language -- the page renders them verbatim.
  const digest = useInsightDigest(locale);
  const funnel = usePipelineFunnel();
  const rates = useResponseRate();
  // The kept letters (19.4): the digest as the night composed it, week by week.
  const letters = useWeeklyDigests();
  const compose = useComposeWeeklyDigest();
  const data = digest.data;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{t("analysis.title")}</h1>
          <p className="text-sm text-muted-foreground">{t("analysis.description")}</p>
        </div>
        <Button variant="outline" size="sm" onClick={() => void digest.refetch()}>
          {t("common.refresh")}
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
          title={t("analysis.loadFailed")}
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
              <CardDescription>{t("analysis.stageMixDescription")}</CardDescription>
            </CardHeader>
            <CardContent>
              {Object.keys(data.stageCounts ?? {}).length > 0 ? (
                <ShareChart
                  data={Object.entries(data.stageCounts ?? {}).map(([stage, count]) => ({
                    label: stageLabel(t, stage),
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
                  {t("analysis.noStageYet")}
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
                  data={funnel.data!.pipeline!.map((stage) => ({
                    label: stageLabel(t, stage.stage ?? ""),
                    value: stage.count ?? 0,
                    detail: `${percent(stage.conversionFromApplied)} ${t("analysis.ofApplied")}`,
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
                {t("analysis.stalledDescription", { days: data.windowDays ?? 14 })}
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
                          {s.company ?? "—"} · {s.status ? stageLabel(t, s.status) : "—"}
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

          {/* 19.4 — the letters the night filed, week by week */}
          <WeeklyLetterCard
            letters={letters.data}
            pending={letters.isPending}
            failed={letters.isError}
            composing={compose.isPending}
            onCompose={() => compose.mutate()}
          />

          {/* Signals */}
          {(data.signals?.length ?? 0) > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>{t("analysis.insights")}</CardTitle>
                <CardDescription>{t("analysis.insightsDescription")}</CardDescription>
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

/**
 * The weekly letter (19.4): the digest as it was composed that week, plus the weeks before.
 *
 * The numbers and the stalled rows are drawn here with the page's own translated words; the
 * payload's engine sentences stay in the record for the email half, because the letter is
 * composed when no reader is present and cannot know whose language to speak.
 */
function WeeklyLetterCard({
  letters,
  pending,
  failed,
  composing,
  onCompose,
}: {
  letters?: WeeklyDigest[];
  pending: boolean;
  failed: boolean;
  composing: boolean;
  onCompose: () => void;
}) {
  const { t, locale } = useLocale();
  const latest = letters?.[0];
  const payload = latest?.payload;
  const stalled = payload?.stalled?.slice(0, 3) ?? [];

  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between gap-3">
        <div>
          <CardTitle>{t("analysis.weeklyTitle")}</CardTitle>
          <CardDescription>{t("analysis.weeklyDescription")}</CardDescription>
        </div>
        <Button variant="outline" size="sm" onClick={onCompose} disabled={composing}>
          {composing ? t("analysis.weeklyComposing") : t("analysis.weeklyCompose")}
        </Button>
      </CardHeader>
      <CardContent>
        {pending ? (
          <LoadingListSkeleton rows={2} />
        ) : failed ? (
          <p className="text-sm text-muted-foreground">{t("analysis.weeklyUnavailable")}</p>
        ) : latest ? (
          <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-2">
              <CalendarDays className="size-4 text-muted-foreground" aria-hidden />
              <p className="text-sm font-medium">
                {t("analysis.weeklyWeek", {
                  date: formatDateOnly(latest.weekStart, locale),
                })}
              </p>
              {latest.generatedAt && (
                <span className="text-xs text-muted-foreground">
                  {relativeTime(latest.generatedAt, locale)}
                </span>
              )}
            </div>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <LetterCell
                label={t("analysis.weeklyApplications")}
                value={formatNumber(payload?.totalApplications)}
              />
              <LetterCell
                label={t("analysis.weeklyQuietCount")}
                value={formatNumber(payload?.stalledCount)}
              />
              <LetterCell
                label={t("analysis.weeklyReply")}
                value={percent(payload?.responseRate)}
              />
              <LetterCell
                label={t("analysis.weeklyOffer")}
                value={percent(payload?.offerRate)}
              />
            </div>
            {stalled.length > 0 && (
              <ul className="space-y-2">
                {stalled.map((s) => (
                  <li
                    key={s.id}
                    className="flex items-center justify-between rounded-lg border border-border/50 p-3"
                  >
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium">
                        {s.title || t("analysis.weeklyUntitled")}
                      </p>
                      <p className="text-xs text-muted-foreground">{s.company ?? "—"}</p>
                    </div>
                    <Badge variant="warning" className="shrink-0">
                      {t("analysis.weeklyQuietDays", { days: s.daysSinceLastActivity ?? 0 })}
                    </Badge>
                  </li>
                ))}
              </ul>
            )}
            {(letters?.length ?? 0) > 1 && (
              <div>
                <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  {t("analysis.weeklyHistory")}
                </p>
                <ul className="space-y-1">
                  {letters!.slice(1, 7).map((letter) => (
                    <li key={letter.id} className="flex items-center justify-between text-sm">
                      <span className="text-muted-foreground">
                        {formatDateOnly(letter.weekStart, locale)}
                      </span>
                      <span className="tabular-nums text-muted-foreground">
                        {formatNumber(letter.payload?.totalApplications)} ·{" "}
                        {formatNumber(letter.payload?.stalledCount)}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ) : (
          <EmptyState
            icon={<CalendarDays aria-hidden />}
            title={t("analysis.weeklyEmpty")}
            description={t("analysis.weeklyEmptyDescription")}
          />
        )}
      </CardContent>
    </Card>
  );
}

/** One number in the weekly letter, labelled in the reader's language. */
function LetterCell({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border/50 p-3">
      <p className="text-lg font-semibold tabular-nums">{value}</p>
      <p className="text-xs text-muted-foreground">{label}</p>
    </div>
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
