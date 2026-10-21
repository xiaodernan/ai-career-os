"use client";

import * as React from "react";
import Link from "next/link";
import {
  ArrowRight,
  Activity as ActivityIcon,
  AlertTriangle,
  Briefcase,
  CheckCircle2,
  FileText,
  Gauge,
  Library,
  ListChecks,
  Sparkles,
  Target,
  TrendingUp,
  Trophy,
  Users,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { PageHeader } from "@/components/common/page-header";
import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { MatchRing, scoreBand } from "@/components/ai/match-ring";
import { SectionHeading } from "@/components/common/export-buttons";
import { LoadingListSkeleton, LoadingMetricGridSkeleton } from "@/components/common/loading-skeletons";
import { SectionBoundary, isEndpointMissing } from "@/components/common/query-boundary";
import { ShareChart } from "@/components/common/bar-chart";
import { useLocale } from "@/lib/i18n/locale-context";
import { missingEndpointMessage } from "@/lib/api/missing-endpoint";
import { JobCard } from "@/components/jobs/job-card";
import { APPLICATION_STAGES, stageLabel, stageMeta, stageShort } from "@/lib/pipeline";
import { useUser } from "@/lib/hooks/auth";
import {
  useActivityRuns,
  useAIUsage,
  useDashboard,
  useDashboardPipeline,
  useJobs,
  useResumes,
} from "@/lib/hooks/resources";
import { runTotalTokens, type NormalizedPage } from "@/lib/api/normalize";
import { formatNumber, relativeTime, titleCase } from "@/lib/format";
import type { ActivityRun, DashboardPayload, Job, Resume } from "@/lib/api/types";

/**
 * Time-of-day greeting, computed client-side only (no fake personalisation).
 *
 * The three words are the product's, so they are read through the locale:
 * a Chinese reader was greeted with "Good evening" on a Chinese page,
 * because the greeting was the one piece of the screen that was written
 * in English in the source.
 */
function useGreeting(t: (key: string) => string): string {
  const [greeting, setGreeting] = React.useState("dashboard.greetingHello");
  React.useEffect(() => {
    const h = new Date().getHours();
    setGreeting(
      h < 12 ? "dashboard.greetingMorning" : h < 18 ? "dashboard.greetingAfternoon" : "dashboard.greetingEvening"
    );
  }, []);
  return t(greeting);
}

export default function DashboardPage() {
  const { t } = useLocale();
  const greeting = useGreeting(t);
  const { data: user } = useUser();
  const dashboard = useDashboard();
  const pipeline = useDashboardPipeline();
  const resumes = useResumes();
  // F8.2's spend line: the summary endpoint has existed with no consumer, so the numbers
  // the activity log bills were nowhere the user could see them.
  const aiUsage = useAIUsage();

  const data = dashboard.data;
  const metrics = data?.metrics;
  const hasMetrics = metrics && Object.values(metrics).some((v) => v != null);
  // The attention card and the "needs attention" stat read the same response field by field:
  // `attention` carries the first few rows, `metrics.needsAttention` the full count.
  const attention = data?.attention ?? [];
  const attentionTotal = metrics?.needsAttention ?? attention.length;

  // The dashboard aggregate may omit sections; fall back to the real list
  // endpoints (never to invented data) so the Command Center stays useful.
  const fallbackJobs = useJobs({ size: 3 });
  const fallbackRuns = useActivityRuns({ size: 5 });

  const recommendedJobs: Job[] = data?.recommendedJobs?.length
    ? data.recommendedJobs
    : (fallbackJobs.data?.items ?? []).slice(0, 3);
  const recentRuns: ActivityRun[] = data?.recentRuns?.length
    ? data.recentRuns
    : (fallbackRuns.data?.items ?? []).slice(0, 5);

  const resumeRow = data?.resume ?? null;
  const pipelineCounts = pipeline.data ?? [];

  const workspaceEmpty =
    !dashboard.isPending &&
    !hasMetrics &&
    !pipelineCounts.length &&
    !recommendedJobs.length &&
    (resumes.data?.items.length ?? 0) === 0;

  return (
    <div className="space-y-8">
      <PageHeader
        title={
          <>
            {greeting},{" "}
            <span className="italic text-primary">
              {user?.displayName?.split(" ")[0] ?? "welcome"}
            </span>
          </>
        }
        description={t("dashboard.description")}
        actions={
          <>
            <Button variant="ai" asChild>
              <Link href="/copilot">
                <Sparkles aria-hidden />
                {t("dashboard.askCopilot")}
              </Link>
            </Button>
            <Button variant="outline" asChild>
              <Link href="/applications">
                {t("dashboard.openPipeline")}
                <ArrowRight aria-hidden />
              </Link>
            </Button>
          </>
        }
      />

      {/* Adaptive onboarding when the workspace holds nothing yet */}
      {workspaceEmpty ? (
        <OnboardingCard hasResume={(resumes.data?.items.length ?? 0) > 0} />
      ) : (
        <>
          {/* Stat strip */}
          {dashboard.isPending ? (
            <LoadingMetricGridSkeleton />
          ) : hasMetrics ? (
            <div
              className={cn(
                "grid gap-4 sm:grid-cols-2",
                // The attention count used to be evicted from the strip the moment an average
                // match existed — two facts about the same search, never both on screen. With five
                // slots the ring and the count coexist.
                typeof metrics.avgMatch === "number" ? "xl:grid-cols-5" : "xl:grid-cols-4"
              )}
            >
              <StatCard
                icon={<Briefcase className="size-4" aria-hidden />}
                label={t("dashboard.applications")}
                value={metrics.applications ?? metrics.inPipeline}
                hint={t("dashboard.rolesInFlight")}
              />
              <StatCard
                icon={<Target className="size-4" aria-hidden />}
                label={t("dashboard.interviews")}
                value={metrics.interviews}
                hint={t("dashboard.reachedOrPracticed")}
              />
              <StatCard
                icon={<Trophy className="size-4" aria-hidden />}
                label={t("dashboard.offers")}
                value={metrics.offers}
                hint={t("dashboard.readyForDecision")}
              />
              {typeof metrics.avgMatch === "number" ? (
                <Card>
                  <CardContent className="flex items-center gap-3">
                    <MatchRing value={metrics.avgMatch} size={56} thickness={5} label={t("dashboard.averageMatch")} />
                    <div>
                      <p className="text-2xs font-medium tracking-wide text-muted-foreground uppercase">
                        {t("dashboard.avgMatchLabel")}
                      </p>
                      <p className="mt-0.5 text-xs text-muted-foreground">
                        {t("dashboard.avgMatchBody")}
                      </p>
                    </div>
                  </CardContent>
                </Card>
              ) : null}
              <StatCard
                icon={<Gauge className="size-4" aria-hidden />}
                label={t("dashboard.needsAttention")}
                value={metrics.needsAttention}
                hint={t("dashboard.staleOrDue")}
              />
            </div>
          ) : dashboard.isError && isEndpointMissing(dashboard.error) ? (
            <Card>
              <CardContent>
                <EmptyState
                  icon={<Gauge aria-hidden />}
                  title={t("dashboard.statsNotConnected")}
                  description={`${missingEndpointMessage("GET /reports/dashboard")} The rest of the page still reads the real APIs below.`}
                  action={
                    <Button variant="outline" size="sm" onClick={() => void dashboard.refetch()}>
                      {t("common.checkAgain")}
                    </Button>
                  }
                />
              </CardContent>
            </Card>
          ) : dashboard.isError ? (
            <Card>
              <CardContent>
                <ErrorState
                  title={t("dashboard.statsFailed")}
                  error={dashboard.error}
                  onRetry={() => void dashboard.refetch()}
                  retrying={dashboard.isFetching}
                />
              </CardContent>
            </Card>
          ) : null}

          <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_22rem]">
            <div className="min-w-0 space-y-4">
              {/* Pipeline mini-kanban */}
              <Card>
                <CardHeader className="pb-3">
                  <SectionHeading
                    eyebrow={t("eyebrows.applications")}
                    icon={<ListChecks className="size-4" aria-hidden />}
                    title={t("dashboard.pipeline")}
                    description={t("dashboard.pipelineDescription")}
                    action={
                      <Button variant="ghost" size="xs" asChild>
                        <Link href="/applications">
                          {t("dashboard.openBoard")}
                          <ArrowRight aria-hidden />
                        </Link>
                      </Button>
                    }
                  />
                </CardHeader>
                <CardContent>
                  <SectionBoundary
                    query={pipeline}
                    skeleton={
                      <div className="grid grid-cols-4 gap-2 xl:grid-cols-7" aria-hidden>
                        {Array.from({ length: 7 }).map((_, i) => (
                          <div key={i} className="h-16 animate-pulse rounded-lg bg-muted" />
                        ))}
                      </div>
                    }
                    empty={{
                      icon: <ListChecks aria-hidden />,
                      title: t("dashboard.emptyPipeline"),
                      description:
                        t("dashboard.emptyPipelineDescription"),
                      action: (
                        <Button variant="ai" size="sm" asChild>
                          <Link href="/jobs">
                            <Briefcase aria-hidden />
                            {t("dashboard.browseJobs")}
                          </Link>
                        </Button>
                      ),
                    }}
                  >
                    {(rows) => {
                      const counts = new Map(rows.map((r) => [r.status, r.count]));
                      const known = new Set<string>(APPLICATION_STAGES.map((s) => s.value));
                      const total = rows.reduce((sum, r) => sum + r.count, 0);
                      return (
                        <div>
                          <ul className="grid grid-cols-4 gap-2 xl:grid-cols-7">
                            {APPLICATION_STAGES.map((stage) => {
                              const count = counts.get(stage.value) ?? 0;
                              return (
                                <li key={stage.value}>
                                  <Link
                                    href="/applications"
                                    className={cn(
                                      "flex h-full flex-col gap-1 rounded-lg border border-border/60 bg-muted/30 p-2.5 transition-colors duration-150 hover:border-primary/40 hover:bg-accent/40 focus-visible:ring-[3px] focus-visible:ring-primary/30",
                                      count === 0 && "opacity-60"
                                    )}
                                  >
                                    <span className="flex items-center gap-1.5">
                                      <span
                                        className={cn("size-1.5 rounded-full", stageMeta(stage.value).dotClass)}
                                        aria-hidden
                                      />
                                      <span className="truncate text-2xs font-medium text-muted-foreground">
                                        {stageLabel(t, stage.value)}
                                      </span>
                                    </span>
                                    <span className="text-lg font-semibold tabular-nums">{count}</span>
                                  </Link>
                                </li>
                              );
                            })}
                          </ul>
                          {rows
                            .filter((r) => !known.has(r.status))
                            .map((r) => (
                              <p key={r.status} className="mt-2 text-xs text-muted-foreground">
                                {titleCase(r.status)}: {r.count}
                              </p>
                            ))}
                          <p className="mt-2 text-xs text-muted-foreground" aria-live="polite">
                            {total === 0
                              ? t("dashboard.boardIsEmpty")
                              : t("dashboard.trackedApplications", {
                                  count: total,
                                  plural: total === 1 ? "" : "s",
                                })}
                          </p>
                        </div>
                      );
                    }}
                  </SectionBoundary>
                </CardContent>
              </Card>

              {/* The rows behind the "Needs attention" stat (§22) — same predicate, so the strip
                  and this card can never disagree about how many applications are waiting. */}
              <Card>
                <CardHeader className="pb-3">
                  <SectionHeading
                    eyebrow={t("eyebrows.waitingOnYou")}
                    icon={<AlertTriangle className="size-4" aria-hidden />}
                    title={t("dashboard.attention")}
                    description={t("dashboard.attentionDescription")}
                    action={
                      <Button variant="ghost" size="xs" asChild>
                        <Link href="/applications">
                          {t("dashboard.openBoard")}
                          <ArrowRight aria-hidden />
                        </Link>
                      </Button>
                    }
                  />
                </CardHeader>
                <CardContent>
                  {dashboard.isPending ? (
                    <LoadingListSkeleton rows={2} />
                  ) : dashboard.isError ? (
                    <ErrorState
                      title={t("dashboard.attentionFailed")}
                      error={dashboard.error}
                      onRetry={() => void dashboard.refetch()}
                      retrying={dashboard.isFetching}
                    />
                  ) : !attention.length ? (
                    <EmptyState
                      icon={<CheckCircle2 aria-hidden />}
                      title={t("dashboard.noAttention")}
                      description={t("dashboard.noAttentionDescription")}
                    />
                  ) : (
                    <ul className="divide-y divide-border/60">
                      {attention.map((row) => {
                        const meta = stageMeta(row.status ?? "");
                        const due = row.reason === "reminder_due";
                        return (
                          <li key={row.id}>
                            <Link
                              href={`/applications?application=${encodeURIComponent(row.id)}`}
                              className="-mx-2.5 flex items-start gap-3 rounded-lg p-2.5 transition-colors duration-150 hover:bg-accent/40 focus-visible:ring-[3px] focus-visible:ring-primary/30"
                            >
                              <span
                                className={cn(
                                  "mt-1.5 size-1.5 shrink-0 rounded-full",
                                  due ? "bg-warning" : "bg-muted-foreground/50"
                                )}
                                aria-hidden
                              />
                              <span className="min-w-0 flex-1">
                                <span className="flex items-center gap-2">
                                  <span className="truncate text-sm font-medium">{row.title}</span>
                                  <Badge variant={meta.badgeVariant} className="shrink-0">
                                    {stageShort(t, row.status ?? "")}
                                  </Badge>
                                </span>
                                <span className="mt-0.5 block truncate text-xs text-muted-foreground">
                                  {row.companyName ? `${row.companyName} · ` : ""}
                                  {due && row.reminderAt
                                    ? t("dashboard.reminderDue", { when: relativeTime(row.reminderAt) })
                                    : row.updatedAt
                                      ? t("dashboard.lastStep", { when: relativeTime(row.updatedAt) })
                                      : t("dashboard.noStep")}
                                </span>
                              </span>
                            </Link>
                          </li>
                        );
                      })}
                    </ul>
                  )}
                  {/* Only when rows are shown: with none listed the empty state above already
                      speaks, and a count line under it would read as a contradiction. */}
                  {attention.length > 0 && attentionTotal > attention.length ? (
                    <p className="mt-3 text-xs text-muted-foreground">
                      {t("dashboard.moreNeedAttention", {
                        count: attentionTotal - attention.length,
                      })}
                    </p>
                  ) : null}
                </CardContent>
              </Card>

              {/* Recommended jobs with match rings */}
              <Card>
                <CardHeader className="pb-3">
                  <SectionHeading
                    eyebrow={t("eyebrows.recommendations")}
                    icon={<Sparkles className="size-4" aria-hidden />}
                    title={t("dashboard.whereToFocus")}
                    description={
                      data?.recommendedJobs?.length
                        ? "Ranked by the matching agent against your resume."
                        : "Straight from the job board — run a match to rank them."
                    }
                    action={
                      <Button variant="ghost" size="xs" asChild>
                        <Link href="/jobs">
                          {t("dashboard.allJobs")}
                          <ArrowRight aria-hidden />
                        </Link>
                      </Button>
                    }
                  />
                </CardHeader>
                <CardContent className="space-y-3">
                  {recommendedJobs.length ? (
                    <ul className="space-y-3">
                      {recommendedJobs.map((job) => (
                        <li key={job.id}>
                          <JobCard job={job} dense />
                        </li>
                      ))}
                    </ul>
                  ) : fallbackJobs.isPending || (!data?.recommendedJobs?.length && dashboard.isPending) ? (
                    <LoadingListSkeleton rows={3} />
                  ) : fallbackJobs.isError && !data?.recommendedJobs?.length ? (
                    <ErrorState
                      title={t("dashboard.recommendationsFailed")}
                      error={fallbackJobs.error}
                      onRetry={() => void fallbackJobs.refetch()}
                      retrying={fallbackJobs.isFetching}
                    />
                  ) : (
                    <EmptyState
                      icon={<Briefcase aria-hidden />}
                      title={t("dashboard.noRecommendations")}
                      description={t("dashboard.noRecommendationsDescription")}
                      action={
                        <Button variant="ai" size="sm" asChild>
                          <Link href="/jobs">
                            <Target aria-hidden />
                            {t("dashboard.goToJobs")}
                          </Link>
                        </Button>
                      }
                    />
                  )}
                </CardContent>
              </Card>

              {/* Recent AI runs */}
              <Card>
                <CardHeader className="pb-3">
                  <SectionHeading
                    eyebrow={t("eyebrows.agentActivity")}
                    icon={<ActivityIcon className="size-4" aria-hidden />}
                    title={t("dashboard.recentRuns")}
                    description={t("dashboard.recentRunsDescription")}
                    action={
                      <Button variant="ghost" size="xs" asChild>
                        <Link href="/activity">
                          {t("dashboard.fullLog")}
                          <ArrowRight aria-hidden />
                        </Link>
                      </Button>
                    }
                  />
                </CardHeader>
                <CardContent>
                  {recentRuns.length ? (
                    <RunFeed runs={recentRuns} />
                  ) : fallbackRuns.isPending && !data?.recentRuns ? (
                    <LoadingListSkeleton rows={3} />
                  ) : fallbackRuns.isError && !data?.recentRuns ? (
                    <ErrorState
                      title={t("dashboard.runsFailed")}
                      error={fallbackRuns.error}
                      onRetry={() => void fallbackRuns.refetch()}
                      retrying={fallbackRuns.isFetching}
                    />
                  ) : (
                    <EmptyState
                      icon={<ActivityIcon aria-hidden />}
                      title={t("dashboard.noRuns")}
                      description={t("dashboard.noRunsDescription")}
                    />
                  )}
                </CardContent>
              </Card>
            </div>

            <aside className="space-y-4">
              {/* Resume score widget */}
              <Card>
                <CardHeader className="pb-3">
                  <SectionHeading
                    eyebrow={t("eyebrows.currentResume")}
                    icon={<FileText className="size-4" aria-hidden />}
                    title={resumeRow?.title ?? resumes.data?.items[0]?.title ?? "Resume"}
                    description={
                      resumeRow
                        ? `${titleCase(resumeRow.status)} · ${resumeRow.currentVersionId ? "structured profile ready" : "awaiting parse"}`
                        : "The version every agent scores against."
                    }
                    action={
                      <Button variant="ghost" size="xs" asChild>
                        <Link href={resumeRow?.id ? `/resumes/${resumeRow.id}` : "/resumes"}>
                          {t("dashboard.open")}
                          <ArrowRight aria-hidden />
                        </Link>
                      </Button>
                    }
                  />
                </CardHeader>
                <CardContent className="space-y-3">
                  <ResumeScore data={data} resumes={resumes} />
                </CardContent>
              </Card>

              {/* Knowledge base pulse */}
              <Card>
                <CardHeader className="pb-3">
                  <SectionHeading
                    eyebrow={t("eyebrows.knowledgeBase")}
                    icon={<Library className="size-4" aria-hidden />}
                    title={t("dashboard.knowledgeBase")}
                    description={t("dashboard.knowledgeBaseDescription")}
                    action={
                      <Button variant="ghost" size="xs" asChild>
                        <Link href="/knowledge">
                          {t("dashboard.manage")}
                          <ArrowRight aria-hidden />
                        </Link>
                      </Button>
                    }
                  />
                </CardHeader>
                <CardContent>
                  <SectionBoundary
                    query={resumes}
                    skeleton={<LoadingListSkeleton rows={2} />}
                    empty={{
                      icon: <Library aria-hidden />,
                      title: t("dashboard.emptyResumes"),
                      description:
                        t("dashboard.emptyResumesDescription"),
                      action: (
                        <Button variant="ai" size="sm" asChild>
                          <Link href="/resumes">
                            <FileText aria-hidden />
                            {t("dashboard.uploadResume")}
                          </Link>
                        </Button>
                      ),
                    }}
                  >
                    {(page) => (
                      <ul className="space-y-2">
                        {page.items.slice(0, 4).map((r) => (
                          <li key={r.id} className="flex items-center gap-2.5">
                            <span className="flex size-7 items-center justify-center rounded-lg bg-muted text-muted-foreground">
                              <FileText className="size-3.5" aria-hidden />
                            </span>
                            <Link
                              href={`/resumes/${r.id}`}
                              className="min-w-0 flex-1 truncate text-sm hover:underline focus-visible:ring-[3px] focus-visible:ring-primary/30 rounded-md"
                            >
                              {r.title}
                            </Link>
                            <StatusPill status={r.status} />
                          </li>
                        ))}
                      </ul>
                    )}
                  </SectionBoundary>
                </CardContent>
              </Card>

              {/* AI usage — what the agents have billed, read from /ai-usage/summary. */}
              <Card>
                <CardHeader className="pb-3">
                  <SectionHeading
                    eyebrow={t("eyebrows.aiUsage")}
                    icon={<Sparkles className="size-4" aria-hidden />}
                    title={t("dashboard.aiUsage")}
                    description={t("dashboard.aiUsageDescription")}
                    action={
                      <Button variant="ghost" size="xs" asChild>
                        <Link href="/activity">
                          {t("dashboard.detail")}
                          <ArrowRight aria-hidden />
                        </Link>
                      </Button>
                    }
                  />
                </CardHeader>
                <CardContent>
                  {aiUsage.isPending ? (
                    <LoadingListSkeleton rows={1} />
                  ) : aiUsage.isError ? (
                    <ErrorState
                      title={t("dashboard.spendFailed")}
                      error={aiUsage.error}
                      onRetry={() => void aiUsage.refetch()}
                      retrying={aiUsage.isFetching}
                    />
                  ) : (aiUsage.data?.requests ?? 0) > 0 ? (
                    <dl className="grid grid-cols-3 gap-2 text-center">
                      <div>
                        <dt className="text-2xs font-medium tracking-wide text-muted-foreground uppercase">
                          {t("dashboard.requests")}
                        </dt>
                        <dd className="mt-0.5 text-lg font-semibold tabular-nums">
                          {formatNumber(aiUsage.data!.requests)}
                        </dd>
                      </div>
                      <div>
                        <dt className="text-2xs font-medium tracking-wide text-muted-foreground uppercase">
                          {t("dashboard.tokensLabel")}
                        </dt>
                        <dd className="mt-0.5 text-lg font-semibold tabular-nums">
                          {formatNumber(aiUsage.data!.totalTokens)}
                        </dd>
                      </div>
                      <div>
                        <dt className="text-2xs font-medium tracking-wide text-muted-foreground uppercase">
                          {t("dashboard.costLabel")}
                        </dt>
                        <dd className="mt-0.5 text-lg font-semibold tabular-nums">
                          ${(aiUsage.data!.costUsd ?? 0).toFixed(2)}
                        </dd>
                      </div>
                    </dl>
                  ) : (
                    <EmptyState
                      icon={<Sparkles aria-hidden />}
                      title={t("dashboard.noSpend")}
                      description={t("dashboard.noSpendDescription")}
                    />
                  )}
                </CardContent>
              </Card>

              {/* Skill gaps summary — rendered even when empty: a card that vanishes without a
                  trace reads as "not built yet" rather than "nothing to fix", so the empty state
                  says which action fills it. */}
              <Card>
                <CardHeader className="pb-3">
                  <SectionHeading
                    eyebrow={t("eyebrows.gapAnalysis")}
                    icon={<TrendingUp className="size-4" aria-hidden />}
                    title={t("dashboard.skillGaps")}
                    description={t("dashboard.skillGapsDescription")}
                  />
                </CardHeader>
                <CardContent className="space-y-2">
                  {(data?.skillGaps?.length ?? 0) > 0 ? (
                    data!.skillGaps!.slice(0, 5).map((g, i) => (
                      <div key={`${g.skill}-${i}`} className="flex items-start gap-2 text-sm">
                        <Badge
                          variant={g.importance === "critical" || g.importance === "high" ? "warning" : "outline"}
                          className="mt-0.5 shrink-0 text-2xs font-normal capitalize"
                        >
                          {g.importance ?? "gap"}
                        </Badge>
                        <div className="min-w-0">
                          <p className="font-medium">{g.skill}</p>
                          {g.reason && <p className="text-xs text-muted-foreground">{g.reason}</p>}
                        </div>
                      </div>
                    ))
                  ) : dashboard.isPending ? (
                    <LoadingListSkeleton rows={3} />
                  ) : dashboard.isError ? (
                    <ErrorState
                      title={t("dashboard.gapsFailed")}
                      error={dashboard.error}
                      onRetry={() => void dashboard.refetch()}
                      retrying={dashboard.isFetching}
                    />
                  ) : (
                    <EmptyState
                      icon={<TrendingUp aria-hidden />}
                      title={t("dashboard.noGaps")}
                      description={t("dashboard.noGapsDescription")}
                      action={
                        <Button variant="outline" size="sm" asChild>
                          <Link href="/jobs">
                            {t("dashboard.openJobs")}
                            <ArrowRight aria-hidden />
                          </Link>
                        </Button>
                      }
                    />
                  )}
                </CardContent>
              </Card>

              {/* Follow-up reminders — contacts ranked by their relation's cadence (11.3) */}
              <Card>
                <CardHeader className="pb-3">
                  <SectionHeading
                    eyebrow={t("eyebrows.networking")}
                    icon={<Users className="size-4" aria-hidden />}
                    title={t("dashboard.followUps")}
                    description={t("dashboard.followUpsDescription")}
                    action={
                      <Button variant="ghost" size="xs" asChild>
                        <Link href="/networking">
                          {t("dashboard.open")}
                          <ArrowRight aria-hidden />
                        </Link>
                      </Button>
                    }
                  />
                </CardHeader>
                <CardContent className="space-y-3">
                  {(data?.followUps?.length ?? 0) > 0 ? (
                    <>
                      {/* The engine already ranked these rows, so the split is
                          read off them rather than recomputed here: a second
                          cadence rule on this side would be a second answer to
                          the same question. */}
                      <ShareChart
                        data={Object.entries(
                          (data!.followUps ?? []).reduce<Record<string, number>>((acc, f) => {
                            const key = f.priority ?? "fresh";
                            acc[key] = (acc[key] ?? 0) + 1;
                            return acc;
                          }, {})
                        ).map(([priority, count]) => ({
                          label: priority,
                          value: count,
                          tone:
                            priority === "overdue"
                              ? ("destructive" as const)
                              : priority === "soon"
                                ? ("warning" as const)
                                : ("muted" as const),
                        }))}
                      />
                      {data!.followUps!.slice(0, 3).map((f) => (
                        <div key={f.id} className="flex items-start gap-2 text-sm">
                          <Badge
                            variant={f.priority === "overdue" ? "destructive" : "warning"}
                            className="mt-0.5 shrink-0 text-2xs font-normal capitalize"
                          >
                            {f.priority}
                          </Badge>
                          <div className="min-w-0">
                            <p className="font-medium">{f.name}</p>
                            <p className="text-xs text-muted-foreground">
                              {[f.company, f.relation].filter(Boolean).join(" · ") || "—"}
                              {f.daysSince != null && ` · ${f.daysSince}d ago`}
                            </p>
                          </div>
                        </div>
                      ))}
                    </>
                  ) : dashboard.isPending ? (
                    <LoadingListSkeleton rows={2} />
                  ) : (
                    <EmptyState
                      icon={<Users aria-hidden />}
                      title={t("dashboard.noFollowUps")}
                      description={t("dashboard.noFollowUpsDescription")}
                      action={
                        <Button variant="outline" size="sm" asChild>
                          <Link href="/networking">
                            {t("dashboard.openNetworking")}
                            <ArrowRight aria-hidden />
                          </Link>
                        </Button>
                      }
                    />
                  )}
                </CardContent>
              </Card>
            </aside>
          </div>
        </>
      )}
    </div>
  );
}

/* ------------------------------- fragments -------------------------------- */

function StatCard({
  icon,
  label,
  value,
  hint,
}: {
  icon: React.ReactNode;
  label: string;
  value?: number;
  hint: string;
}) {
  return (
    <Card>
      <CardHeader>
        <CardDescription className="flex items-center gap-1.5">
          <span className="text-muted-foreground [&_svg]:size-3.5">{icon}</span>
          {label}
        </CardDescription>
        <CardTitle className="text-2xl font-semibold tabular-nums">
          {value ?? value === 0 ? formatNumber(value) : "—"}
        </CardTitle>
      </CardHeader>
      <CardContent className="text-xs text-muted-foreground">{hint}</CardContent>
    </Card>
  );
}

function RunFeed({ runs }: { runs: ActivityRun[] }) {
  const { t } = useLocale();
  return (
    <ul className="divide-y divide-border/50">
      {runs.map((run) => {
        const ok = run.status === "ok" || run.status === "completed" || run.status === "success";
        const failed = run.status === "error" || run.status === "failed";
        const tokens = runTotalTokens(run);
        return (
          <li key={run.id} className="flex items-center gap-3 py-2.5 first:pt-0 last:pb-0">
            <span
              className={cn(
                "size-1.5 shrink-0 rounded-full",
                failed ? "bg-destructive" : ok ? "bg-success" : "bg-warning"
              )}
              aria-hidden
            />
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm">
                {`${run.agent ?? "agent"} · ${run.kind ?? "run"}`}
              </p>
              <p className="truncate text-xs text-muted-foreground">
                {relativeTime(run.startedAt)}
                {tokens ? ` · ${formatNumber(tokens)} tokens` : ""}
              </p>
            </div>
            <Button variant="link" size="xs" asChild className="shrink-0">
              <Link href={`/activity/${run.id}`}>
                {t("dashboard.trace")}
                <ArrowRight aria-hidden />
              </Link>
            </Button>
          </li>
        );
      })}
    </ul>
  );
}

function ResumeScore({
  data,
  resumes,
}: {
  data: DashboardPayload | null | undefined;
  resumes: { data?: NormalizedPage<Resume> };
}) {
  const { t } = useLocale();
  const score =
    (typeof data?.score === "number" ? data.score : data?.score?.overall) ??
    (typeof data?.resume?.score === "number" ? data.resume.score : data?.resume?.score?.overall) ??
    resumes.data?.items.find((r) => typeof r.score === "object" ? r.score?.overall : undefined)?.score?.overall;

  if (score == null) {
    return (
      <EmptyState
        className="py-6"
        icon={<Gauge aria-hidden />}
        title={t("dashboard.noResumeScore")}
        description={t("dashboard.noResumeScoreDescription")}
        action={
          <Button variant="ai" size="sm" asChild>
            <Link href="/resumes">
              <FileText aria-hidden />
              {t("dashboard.uploadResume")}
            </Link>
          </Button>
        }
      />
    );
  }

  const band = scoreBand(score);
  return (
    <div className="flex items-center gap-4">
      <MatchRing value={score} size={68} thickness={6} label={t("dashboard.resumeScore")} />
      <div className="min-w-0 text-sm">
        <p className={cn("font-medium", band === "strong" && "text-success", band === "good" && "text-primary", band === "fair" && "text-warning", band === "weak" && "text-destructive")}>
          {band === "strong" ? "Interview-ready" : band === "good" ? "Solid baseline" : band === "fair" ? "Needs work" : "Weak — start here"}
        </p>
        <p className="mt-0.5 text-xs text-muted-foreground">
          Overall grade from the resume reviewer. Open the resume for the per-dimension breakdown.
        </p>
      </div>
    </div>
  );
}

function StatusPill({ status }: { status: string }) {
  const variant =
    status === "parsed" || status === "ready"
      ? "success"
      : status === "failed"
        ? "destructive"
        : status === "parsing" || status === "ingesting"
          ? "warning"
          : "secondary";
  return (
    <Badge variant={variant} className="shrink-0 text-2xs font-normal capitalize">
      {status}
    </Badge>
  );
}

function OnboardingCard({ hasResume }: { hasResume: boolean }) {
  const { t } = useLocale();
  const steps = [
    {
      done: hasResume,
      icon: <FileText className="size-4" aria-hidden />,
      title: t("dashboard.stepUpload"),
      description: t("dashboard.stepUploadDescription"),
      href: "/resumes",
      cta: "Upload",
    },
    {
      done: false,
      icon: <Briefcase className="size-4" aria-hidden />,
      title: t("dashboard.stepJd"),
      description: t("dashboard.stepJdDescription"),
      href: "/jobs",
      cta: "Paste a JD",
    },
    {
      done: false,
      icon: <Target className="size-4" aria-hidden />,
      title: t("dashboard.stepMatch"),
      description: t("dashboard.stepMatchDescription"),
      href: "/jobs",
      cta: "Match a job",
    },
    {
      done: false,
      icon: <Users className="size-4" aria-hidden />,
      title: t("dashboard.stepTrack"),
      description: t("dashboard.stepTrackDescription"),
      href: "/applications",
      cta: t("dashboard.openBoard"),
    },
  ];

  return (
    <Card className="animate-fade-up">
      <CardHeader>
        <CardTitle className="text-base flex items-center gap-2">
          <Sparkles className="size-4 text-primary" aria-hidden />
          {t("dashboard.onboardingTitle")}
        </CardTitle>
        <CardDescription>
          {t("dashboard.onboardingDescription")}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ol className="grid gap-3 sm:grid-cols-2">
          {steps.map((s, i) => (
            <li
              key={s.title}
              className={cn(
                "flex gap-3 rounded-xl border p-4",
                s.done ? "border-success/30 bg-success/5" : "border-border/70 bg-muted/20"
              )}
            >
              <span
                className={cn(
                  "mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-lg",
                  s.done ? "bg-success/15 text-success" : "bg-muted text-muted-foreground"
                )}
                aria-hidden
              >
                {s.done ? <CheckCircle2 className="size-4" /> : s.icon}
              </span>
              <div className="min-w-0">
                <p className="text-sm font-medium">
                  <span className="mr-1.5 text-xs text-muted-foreground tabular-nums">{i + 1}.</span>
                  {s.title}
                </p>
                <p className="mt-0.5 text-xs text-muted-foreground">{s.description}</p>
                <Button variant={s.done ? "ghost" : "outline"} size="xs" className="mt-2" asChild>
                  <Link href={s.href}>
                    {s.done ? "Open" : s.cta}
                    <ArrowRight aria-hidden />
                  </Link>
                </Button>
              </div>
            </li>
          ))}
        </ol>
        <Separator className="my-4" />
        <p className="text-xs text-muted-foreground">
          {t("dashboard.preferToTalk")}{" "}
          <Link href="/copilot" className="font-medium text-primary underline-offset-4 hover:underline">
            {t("dashboard.openCopilot")}
          </Link>{" "}
          {t("dashboard.preferToTalkBody")}
        </p>
      </CardContent>
    </Card>
  );
}
