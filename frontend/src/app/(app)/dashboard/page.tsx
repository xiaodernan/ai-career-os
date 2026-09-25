"use client";

import * as React from "react";
import Link from "next/link";
import {
  ArrowRight,
  Activity as ActivityIcon,
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
import { MatchRing, scoreBand } from "@/components/ai/match-ring";
import { AIBadge } from "@/components/ai/ai-badge";
import { SectionHeading } from "@/components/common/export-buttons";
import { LoadingListSkeleton, LoadingMetricGridSkeleton } from "@/components/common/loading-skeletons";
import { SectionBoundary, isEndpointMissing } from "@/components/common/query-boundary";
import { JobCard } from "@/components/jobs/job-card";
import { APPLICATION_STAGES, stageMeta } from "@/lib/pipeline";
import { useUser } from "@/lib/hooks/auth";
import {
  useActivityRuns,
  useDashboard,
  useDashboardPipeline,
  useJobs,
  useResumes,
} from "@/lib/hooks/resources";
import { runTotalTokens, type NormalizedPage } from "@/lib/api/normalize";
import { formatNumber, relativeTime, titleCase } from "@/lib/format";
import type { ActivityRun, DashboardPayload, Job, Resume } from "@/lib/api/types";

/** Time-of-day greeting, computed client-side only (no fake personalisation). */
function useGreeting(): string {
  const [greeting, setGreeting] = React.useState("Hello");
  React.useEffect(() => {
    const h = new Date().getHours();
    setGreeting(h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening");
  }, []);
  return greeting;
}

export default function DashboardPage() {
  const greeting = useGreeting();
  const { data: user } = useUser();
  const dashboard = useDashboard();
  const pipeline = useDashboardPipeline();
  const resumes = useResumes();

  const data = dashboard.data;
  const metrics = data?.metrics;
  const hasMetrics = metrics && Object.values(metrics).some((v) => v != null);

  // The dashboard aggregate may omit sections; fall back to the real list
  // endpoints (never to invented data) so the Command Center stays useful.
  const fallbackJobs = useJobs({ size: 3 });
  const fallbackRuns = useActivityRuns({ limit: 5 });

  const recommendedJobs: Job[] = data?.recommendedJobs?.length
    ? data.recommendedJobs
    : (fallbackJobs.data?.items ?? []).slice(0, 3);
  const recentRuns: ActivityRun[] = data?.recentRuns?.length
    ? data.recentRuns
    : (fallbackRuns.data?.items ?? []).slice(0, 5);

  const resumeRow = data?.resume ?? null;
  const pipelineCounts = pipeline.data ?? [];
  const suggestion = data?.suggestion ?? data?.insights?.[0] ?? null;

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
        description="Your job search at a glance — every figure here is read live from the API."
        actions={
          <>
            <Button variant="ai" asChild>
              <Link href="/copilot">
                <Sparkles aria-hidden />
                Ask Copilot
              </Link>
            </Button>
            <Button variant="outline" asChild>
              <Link href="/applications">
                Open pipeline
                <ArrowRight aria-hidden />
              </Link>
            </Button>
          </>
        }
      />

      {/* One-line AI direction (only when the backend actually says something) */}
      {suggestion && (
        <div className="animate-fade-up flex items-start gap-3 rounded-xl border border-primary/25 bg-primary/5 p-4">
          <span className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <Sparkles className="size-4" aria-hidden />
          </span>
          <div className="min-w-0">
            <p className="flex items-center gap-2 text-2xs font-medium tracking-wide text-primary uppercase">
              Suggested next step <AIBadge />
            </p>
            <p className="mt-0.5 text-sm text-foreground">{suggestion}</p>
          </div>
        </div>
      )}

      {/* Adaptive onboarding when the workspace holds nothing yet */}
      {workspaceEmpty ? (
        <OnboardingCard hasResume={(resumes.data?.items.length ?? 0) > 0} />
      ) : (
        <>
          {/* Stat strip */}
          {dashboard.isPending ? (
            <LoadingMetricGridSkeleton />
          ) : hasMetrics ? (
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              <StatCard
                icon={<Briefcase className="size-4" aria-hidden />}
                label="Applications"
                value={metrics.applications ?? metrics.inPipeline}
                hint="roles in flight"
              />
              <StatCard
                icon={<Target className="size-4" aria-hidden />}
                label="Interviews"
                value={metrics.interviews}
                hint="reached or practiced"
              />
              <StatCard
                icon={<Trophy className="size-4" aria-hidden />}
                label="Offers"
                value={metrics.offers}
                hint="ready for decision"
              />
              {typeof metrics.avgMatch === "number" ? (
                <Card className="sm:col-span-2 xl:col-span-1">
                  <CardContent className="flex items-center gap-3">
                    <MatchRing value={metrics.avgMatch} size={56} thickness={5} label="Average match" />
                    <div>
                      <p className="text-2xs font-medium tracking-wide text-muted-foreground uppercase">
                        Avg match
                      </p>
                      <p className="mt-0.5 text-xs text-muted-foreground">
                        across scored jobs, from your resume evidence
                      </p>
                    </div>
                  </CardContent>
                </Card>
              ) : (
                <StatCard
                  icon={<Gauge className="size-4" aria-hidden />}
                  label="Needs attention"
                  value={metrics.needsAttention}
                  hint="stale or weak spots"
                />
              )}
            </div>
          ) : dashboard.isError && isEndpointMissing(dashboard.error) ? (
            <Card>
              <CardContent>
                <EmptyState
                  icon={<Gauge aria-hidden />}
                  title="Dashboard stats aren't connected yet"
                  description="The /reports/dashboard endpoint isn't live — the rest of the page still reads the real APIs below and no numbers are invented."
                  action={
                    <Button variant="outline" size="sm" onClick={() => void dashboard.refetch()}>
                      Check again
                    </Button>
                  }
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
                    eyebrow="Applications"
                    icon={<ListChecks className="size-4" aria-hidden />}
                    title="Pipeline"
                    description="Counts per stage, live from the applications board."
                    action={
                      <Button variant="ghost" size="xs" asChild>
                        <Link href="/applications">
                          Open board
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
                      title: "Nothing in the pipeline yet",
                      description:
                        "Save a job and start tracking it — the board covers saved → applied → OA → interview → final round → offer.",
                      action: (
                        <Button variant="ai" size="sm" asChild>
                          <Link href="/jobs">
                            <Briefcase aria-hidden />
                            Browse jobs
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
                                        {stage.label}
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
                              ? "The board is empty."
                              : `${total} tracked application${total === 1 ? "" : "s"}.`}
                          </p>
                        </div>
                      );
                    }}
                  </SectionBoundary>
                </CardContent>
              </Card>

              {/* Recommended jobs with match rings */}
              <Card>
                <CardHeader className="pb-3">
                  <SectionHeading
                    eyebrow="Recommendations"
                    icon={<Sparkles className="size-4" aria-hidden />}
                    title="Where to focus"
                    description={
                      data?.recommendedJobs?.length
                        ? "Ranked by the matching agent against your resume."
                        : "Straight from the job board — run a match to rank them."
                    }
                    action={
                      <Button variant="ghost" size="xs" asChild>
                        <Link href="/jobs">
                          All jobs
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
                  ) : (
                    <EmptyState
                      icon={<Briefcase aria-hidden />}
                      title="No jobs to recommend yet"
                      description="Paste a JD or let the research agent fill the board — recommendations appear as soon as there's something to rank."
                      action={
                        <Button variant="ai" size="sm" asChild>
                          <Link href="/jobs">
                            <Target aria-hidden />
                            Go to Jobs
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
                    eyebrow="Agent activity"
                    icon={<ActivityIcon className="size-4" aria-hidden />}
                    title="Recent AI runs"
                    description="Every match, tailor and ingestion the agents performed."
                    action={
                      <Button variant="ghost" size="xs" asChild>
                        <Link href="/activity">
                          Full log
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
                  ) : (
                    <EmptyState
                      icon={<ActivityIcon aria-hidden />}
                      title="No AI runs yet"
                      description="Run a match or tailor a resume and the orchestrator will log every step here."
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
                    eyebrow="Current resume"
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
                          Open
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
                    eyebrow="Knowledge base"
                    icon={<Library className="size-4" aria-hidden />}
                    title="What agents can cite"
                    description="Sources ingestion feeds the retrieval layer."
                    action={
                      <Button variant="ghost" size="xs" asChild>
                        <Link href="/knowledge">
                          Manage
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
                      title: "No resumes in the base yet",
                      description:
                        "Upload your resume — parsing feeds the knowledge base so every AI answer cites real experience.",
                      action: (
                        <Button variant="ai" size="sm" asChild>
                          <Link href="/resumes">
                            <FileText aria-hidden />
                            Upload resume
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

              {/* Skill gaps summary */}
              {(data?.skillGaps?.length ?? 0) > 0 && (
                <Card>
                  <CardHeader className="pb-3">
                    <SectionHeading
                      eyebrow="Gap analysis"
                      icon={<TrendingUp className="size-4" aria-hidden />}
                      title="Top skill gaps"
                      description="Across your matched jobs."
                    />
                  </CardHeader>
                  <CardContent className="space-y-2">
                    {data!.skillGaps!.slice(0, 5).map((g, i) => (
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
                    ))}
                  </CardContent>
                </Card>
              )}
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
                {run.summary ?? `${run.agent ?? "agent"} · ${run.kind ?? "run"}`}
              </p>
              <p className="truncate text-xs text-muted-foreground">
                {relativeTime(run.startedAt ?? run.createdAt)}
                {tokens ? ` · ${formatNumber(tokens)} tokens` : ""}
              </p>
            </div>
            <Button variant="link" size="xs" asChild className="shrink-0">
              <Link href={`/activity/${run.id}`}>
                Trace
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
  const score =
    (typeof data?.score === "number" ? data.score : data?.score?.overall) ??
    (typeof data?.resume?.score === "number" ? data.resume.score : data?.resume?.score?.overall) ??
    resumes.data?.items.find((r) => typeof r.score === "object" ? r.score?.overall : undefined)?.score?.overall;

  if (score == null) {
    return (
      <EmptyState
        className="py-6"
        icon={<Gauge aria-hidden />}
        title="No resume score yet"
        description="Upload and parse a resume — the reviewer agent grades bullets, structure, impact and keyword coverage."
        action={
          <Button variant="ai" size="sm" asChild>
            <Link href="/resumes">
              <FileText aria-hidden />
              Upload resume
            </Link>
          </Button>
        }
      />
    );
  }

  const band = scoreBand(score);
  return (
    <div className="flex items-center gap-4">
      <MatchRing value={score} size={68} thickness={6} label="Resume score" />
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
  const steps = [
    {
      done: hasResume,
      icon: <FileText className="size-4" aria-hidden />,
      title: "Upload your resume",
      description: "Parsing builds the structured profile and knowledge base every agent cites from.",
      href: "/resumes",
      cta: "Upload",
    },
    {
      done: false,
      icon: <Briefcase className="size-4" aria-hidden />,
      title: "Add a job description",
      description: "Paste any JD in Jobs → Analyze a JD to extract requirements and hidden signals.",
      href: "/jobs",
      cta: "Paste a JD",
    },
    {
      done: false,
      icon: <Target className="size-4" aria-hidden />,
      title: "Run your first match",
      description: "The matcher scores you per dimension and cites the resume lines behind every number.",
      href: "/jobs",
      cta: "Match a job",
    },
    {
      done: false,
      icon: <Users className="size-4" aria-hidden />,
      title: "Track the pipeline",
      description: "Saved jobs flow through the kanban: saved → applied → OA → interview → offer.",
      href: "/applications",
      cta: "Open board",
    },
  ];

  return (
    <Card className="animate-fade-up">
      <CardHeader>
        <CardTitle className="text-base flex items-center gap-2">
          <Sparkles className="size-4 text-primary" aria-hidden />
          Let&apos;s build your workspace
        </CardTitle>
        <CardDescription>
          Nothing here is pre-filled — these steps unlock every feature, in order.
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
          Prefer to talk it through? <Link href="/copilot" className="font-medium text-primary underline-offset-4 hover:underline">Open Copilot</Link> and describe
          your target role — it will ask for what it needs.
        </p>
      </CardContent>
    </Card>
  );
}
