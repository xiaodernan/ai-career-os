"use client";

import * as React from "react";
import Link from "next/link";
import { interviewApplicationHref } from "@/lib/interview-target";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  ArrowRight,
  BookOpen,
  ExternalLink,
  FileBarChart,
  Lightbulb,
  ListChecks,
  Play,
  Quote,
  ThumbsDown,
  ThumbsUp,
  TrendingUp,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { PracticeLine } from "@/components/interviews/practice-line";
import { DebriefCard } from "@/components/interviews/debrief-card";
import { BetterAnswerNoteButton } from "@/components/interviews/better-answer-note-button";
import { StudyNoteButton } from "@/components/interviews/study-note-button";
import { GapNoteButton } from "@/components/interviews/gap-note-button";
import { PrepareNoteButton } from "@/components/interviews/prepare-note-button";
import { SectionHeading } from "@/components/common/export-buttons";
import { DimensionBars } from "@/components/common/skill-chips";
import { MatchRing } from "@/components/ai/match-ring";
import { AIBadge } from "@/components/ai/ai-badge";
import { useCreateInterviewSession, useFinalizeInterview } from "@/lib/hooks/actions";
import { useInterviewSession, useInterviewSessions } from "@/lib/hooks/resources";
import { cardPractice, previousRehearsal, scoreDelta } from "@/lib/interview-practice";
import { normalizeInterviewReport, str, type InterviewTrajectoryPoint } from "@/lib/api/normalize";
import { depthBand, depthLevel, formatDate } from "@/lib/format";
import { interviewModeName } from "@/lib/status-words";
import { safeHref } from "@/lib/safe-href";
import { interviewDimensionLabel } from "@/lib/dimensions";
import { useLocale } from "@/lib/i18n/locale-context";

export default function InterviewReportPage() {
  const params = useParams<{ id: string }>();
  const { t, locale } = useLocale();
  const id = params?.id ?? null;
  const session = useInterviewSession(id);
  const finalize = useFinalizeInterview(id ?? "");
  const router = useRouter();
  // 68.1: "Practice again" used to link back to *this* sitting, which is
  // completed -- the runner then only said "finished". The verb belongs to the
  // create route, with the same card (or, for free practice, the same role).
  const restart = useCreateInterviewSession();

  // 59.1: the card's other rehearsals, read only when this session names one.
  // The list already answers each row's score, so the comparison is a fold over
  // one narrow read rather than a new endpoint.
  const siblings = useInterviewSessions({
    applicationId: session.data?.applicationId ?? undefined,
    size: 20,
    enabled: Boolean(session.data?.applicationId),
  });

  const data = session.data;

  if (session.isPending) {
    return (
      <div className="mx-auto max-w-3xl space-y-6">
        <Skeleton className="h-4 w-40" />
        <Skeleton className="h-32 rounded-xl" />
        <Skeleton className="h-64 rounded-xl" />
        <span className="sr-only">{t("interviews.report.loading")}</span>
      </div>
    );
  }

  if (session.isError || !data) {
    return (
      <div className="mx-auto max-w-3xl space-y-6">
        <BackLink id={id} />
        <Card>
          <CardContent>
            <ErrorState
              title={t("interviews.report.loadFailed")}
              error={session.error}
              onRetry={() => void session.refetch()}
              retrying={session.isFetching}
            />
          </CardContent>
        </Card>
      </div>
    );
  }

  const normalized = normalizeInterviewReport(data.report);
  const { overall, well, weak, summary, better, gaps, prepare, study, trajectory } =
    normalized ?? {
      overall: undefined,
      dims: [],
      well: [],
      weak: [],
      summary: undefined,
      better: [],
      gaps: [],
      prepare: [],
      study: [],
      trajectory: [],
    };
  // The rubric's eight names are the product's, not the wire's: the report
  // answers with `technical_accuracy` and the reader is shown "Technical
  // accuracy" -- in their language.
  const dims = (normalized?.dims ?? []).map((d) => ({
    ...d,
    label: interviewDimensionLabel(t, d.key),
  }));

  const hasReport = normalized?.hasContent ?? false;

  const practice = cardPractice(siblings.data?.items ?? [], data.id);

  // 62.2: the same fold that places this sitting names the attempt it followed,
  // so the score can be read against that one instead of standing alone.
  const previous = previousRehearsal(siblings.data?.items ?? [], data.id);
  const delta = scoreDelta(previous?.overall, overall);

  // 60.2: the role is the strongest fact a kept note can carry about where it came
  // from; the date is the fallback for a free rehearsal with no target job.
  const studyOrigin = data.jobTitle
    ? t("interviews.report.noteOriginJob", { job: data.jobTitle })
    : data.startedAt
      ? t("interviews.report.noteOriginDate", { date: formatDate(data.startedAt, locale) })
      : undefined;

  const practiceAgain = () =>
    restart.mutate(
      {
        mode: data.mode,
        ...(data.applicationId
          ? { applicationId: data.applicationId }
          : data.jobTitle
            ? { positionTitle: data.jobTitle }
            : {}),
      },
      {
        onSuccess: (res) => {
          const nextId =
            str(res, "id", "session_id", "sessionId") ??
            str((res as { session?: unknown }).session, "id");
          if (nextId) router.push(`/interviews/${nextId}`);
        },
      }
    );

  if (!hasReport) {
    return (
      <div className="mx-auto max-w-3xl space-y-6">
        <BackLink id={id} />
        <Card>
          <CardContent>
            {data.status === "active" ? (
              <EmptyState
                icon={<FileBarChart aria-hidden />}
                title={t("interviews.report.stillRunning")}
                description={t("interviews.report.stillRunningDescription")}
                action={
                  <Button variant="ai" size="sm" asChild>
                    <Link href={`/interviews/${data.id}`}>
                      {t("interviews.report.continueInterview")}
                      <ArrowRight aria-hidden />
                    </Link>
                  </Button>
                }
              />
            ) : (
              <EmptyState
                icon={<FileBarChart aria-hidden />}
                title={t("interviews.report.noReport")}
                description={t("interviews.report.noReportDescription")}
                action={
                  <Button
                    variant="ai"
                    size="sm"
                    loading={finalize.isPending}
                    onClick={() => finalize.mutate(undefined, { onSuccess: () => void session.refetch() })}
                  >
                    {t("interviews.report.generateReport")}
                  </Button>
                }
              />
            )}
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <BackLink id={id} />

      {/* Overall */}
      <Card className="animate-fade-up">
        <CardHeader className="pb-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <CardTitle className="font-serif text-display-sm text-lg">
                {t("interviews.modeReport", { mode: interviewModeName(t, data.mode) })}
              </CardTitle>
              <CardDescription>
                {data.companyName ? `${data.companyName} · ` : ""}
                {data.jobTitle ? `${data.jobTitle} · ` : ""}
                {data.finishedAt ? formatDate(data.finishedAt, locale) : formatDate(data.startedAt, locale)}
              </CardDescription>
              {interviewApplicationHref(data.applicationId) && (
                <Link
                  href={interviewApplicationHref(data.applicationId)!}
                  className="text-xs text-muted-foreground underline underline-offset-2 hover:text-foreground"
                >
                  {t("interviews.openApplication")}
                </Link>
              )}
              {/* 59.1: one sitting answers "how did it go"; the practice line answers
                  "is it getting better", which is the question a second rehearsal asks. */}
              <PracticeLine
                practice={practice}
                applicationId={data.applicationId}
                className="mt-1"
              />
            </div>
            <AIBadge label={t("interviews.report.evaluatorOutputBadge")} />
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap items-center gap-5">
            {overall != null && (
              <MatchRing
                value={overall}
                size={84}
                thickness={7}
                label={t("interviews.report.overallScore")}
              />
            )}
            <div className="min-w-48 flex-1">
              <p className="text-sm leading-relaxed">
                {summary ??
                  (overall != null
                    ? overall >= 75
                      ? t("interviews.report.strongSession")
                      : t("interviews.report.solidPractice")
                    : t("interviews.report.perDimension"))}
              </p>
              <div className="mt-2 flex flex-wrap gap-2">
                {trajectory.length > 0 && (
                  <Badge variant="outline" className="text-2xs font-normal tabular-nums">
                    {t("interviews.report.questionsCount", { count: trajectory.length })}
                  </Badge>
                )}
                {data.difficulty != null && (
                  <Badge variant="outline" className="text-2xs font-normal tabular-nums">
                    {t("interviews.report.depthReached", {
                      level: depthLevel(data.difficulty),
                      band: t(`interviews.depthBands.${depthBand(data.difficulty)}`),
                    })}
                  </Badge>
                )}
                {delta && (
                  <Badge
                    variant="outline"
                    className={cn(
                      "text-2xs font-normal tabular-nums",
                      delta.delta > 0 && "border-success/40 text-success",
                      delta.delta < 0 && "border-warning/40 text-warning"
                    )}
                  >
                    {delta.delta === 0
                      ? t("interviews.report.sameAsLast", { score: delta.current })
                      : t("interviews.report.comparedToLast", {
                          previous: delta.previous,
                          current: delta.current,
                          delta: `${delta.delta > 0 ? "+" : ""}${delta.delta}`,
                        })}
                  </Badge>
                )}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Your own words first, then the evaluator's verdict — the reader writes
          their debrief before reading the dimensions. */}
      <DebriefCard sessionId={data.id} />

      {/* Dimensions */}
      {dims.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <SectionHeading
              eyebrow={t("eyebrows.rubric")}
              icon={<FileBarChart className="size-4" aria-hidden />}
              title={t("interviews.report.dimensions")}
              description={t("interviews.report.dimensionsDescription")}
            />
          </CardHeader>
          <CardContent>
            <DimensionBars dimensions={dims} />
          </CardContent>
        </Card>
      )}

      {/* Well / weak */}
      <div className="grid gap-4 sm:grid-cols-2">
        {well.length > 0 && (
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-base text-success">
                <ThumbsUp className="size-4" aria-hidden />
                {t("interviews.report.whatWentWell")}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="ml-4 list-disc space-y-1.5 text-sm">
                {well.map((w, i) => (
                  <li key={i}>{w}</li>
                ))}
              </ul>
            </CardContent>
          </Card>
        )}
        {weak.length > 0 && (
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-base text-warning">
                <ThumbsDown className="size-4" aria-hidden />
                {t("interviews.report.whatWasWeak")}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="ml-4 list-disc space-y-1.5 text-sm">
                {weak.map((w, i) => (
                  <li key={i}>{w}</li>
                ))}
              </ul>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Gaps and preparation (61.2) */}
      {(gaps.length > 0 || prepare.length > 0) && (
        <div className="grid gap-4 sm:grid-cols-2">
          {gaps.length > 0 && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-base">
                  <Lightbulb className="size-4" aria-hidden />
                  {t("interviews.report.missingConcepts")}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="ml-4 list-disc space-y-1.5 text-sm">
                  {gaps.map((gap, i) => (
                    /* 63.1: a named gap is advice; keeping it makes it citable. */
                    <li key={i} className="flex items-start justify-between gap-2">
                      <span>{gap}</span>
                      <GapNoteButton gap={gap} origin={studyOrigin} />
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}
          {prepare.length > 0 && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-base">
                  <ListChecks className="size-4" aria-hidden />
                  {t("interviews.report.questionsToPrepare")}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="ml-4 list-disc space-y-1.5 text-sm">
                  {prepare.map((question, i) => (
                    /* 63.2: the question is what the reader will search for later. */
                    <li key={i} className="flex items-start justify-between gap-2">
                      <span>{question}</span>
                      <PrepareNoteButton question={question} origin={studyOrigin} />
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* Better answers (61.1) */}
      {better.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <SectionHeading
              eyebrow={t("eyebrows.betweenSessions")}
              icon={<Quote className="size-4" aria-hidden />}
              title={t("interviews.report.betterAnswers")}
              description={t("interviews.report.betterAnswersDescription")}
            />
          </CardHeader>
          <CardContent className="space-y-4">
            {better.map((b, i) => (
              <div key={i} className="flex items-start gap-3">
                <div className="min-w-0 flex-1 space-y-1.5">
                  {b.question && (
                    <p className="text-xs font-medium text-muted-foreground">{b.question}</p>
                  )}
                  <p className="whitespace-pre-line text-sm leading-relaxed">{b.answer}</p>
                </div>
                {/* 61.3: the rewrite is keepable too -- the question becomes the note's title. */}
                <BetterAnswerNoteButton item={b} origin={studyOrigin} />
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Depth trajectory */}
      {trajectory.length > 0 && <TrajectoryChart points={trajectory} />}

      {/* Study materials */}
      {study.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <SectionHeading
              eyebrow={t("eyebrows.betweenSessions")}
              icon={<BookOpen className="size-4" aria-hidden />}
              title={t("interviews.report.studyMaterial")}
              description={t("interviews.report.studyMaterialDescription")}
            />
          </CardHeader>
          <CardContent>
            <ul className="divide-y divide-border/50">
              {study.map((s, i) => (
                <li key={i} className="flex items-start gap-3 py-2.5 first:pt-0 last:pb-0">
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium">{s.title ?? t("interviews.report.untitledResource")}</p>
                    {s.why && <p className="text-xs text-muted-foreground">{s.why}</p>}
                  </div>
                  {safeHref(s.url) && (
                    <a
                      href={safeHref(s.url)}
                      target="_blank"
                      rel="noopener noreferrer nofollow"
                      className="mt-0.5 flex shrink-0 items-center gap-1 text-xs font-medium text-primary underline-offset-4 hover:underline"
                    >
                      {t("interviews.report.open")}
                      <ExternalLink className="size-3" aria-hidden />
                    </a>
                  )}
                  {/* 60.1: the advice stops being a sentence on a page -- it becomes a
                      note the knowledge base has ingested and the copilot can quote. */}
                  <StudyNoteButton item={s} origin={studyOrigin} />
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* Actions */}
      <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-border/70 bg-muted/20 p-4">
        <p className="text-xs text-muted-foreground">
          {t("interviews.report.practiceHint")}
        </p>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" asChild>
            <Link href="/interviews">{t("interviews.report.allInterviews")}</Link>
          </Button>
          <Button
            variant="ai"
            size="sm"
            loading={restart.isPending}
            disabled={restart.isPending}
            onClick={practiceAgain}
          >
            <Play aria-hidden />
            {t("interviews.report.practiceAgain")}
          </Button>
        </div>
      </div>
    </div>
  );
}

/* ------------------------------- fragments -------------------------------- */

function BackLink({ id }: { id: string | null }) {
  const { t } = useLocale();
  return (
    <Link
      href="/interviews"
      className="-ml-1 inline-flex w-fit items-center gap-1.5 rounded-md px-1 text-sm text-muted-foreground hover:text-foreground focus-visible:ring-[3px] focus-visible:ring-primary/30"
    >
      <ArrowLeft className="size-4" aria-hidden />
      {t("interviews.report.allInterviews")}
      {id ? <span className="sr-only">{t("interviews.report.fromReport", { id })}</span> : null}
    </Link>
  );
}

/**
 * Depth trajectory — x = question order, solid line = how deep the agent had pushed
 * when it asked (run length of follow-ups, 1–5), dotted line = the score it gave.
 * One point per question, from the shared fold in `normalizeTrajectory`; scores are
 * absent on questions that were never answered, and the dotted line skips them.
 */
function TrajectoryChart({ points }: { points: InterviewTrajectoryPoint[] }) {
  const { t } = useLocale();
  const W = 560;
  const H = 150;
  const pad = { l: 8, r: 8, t: 10, b: 22 };
  const innerW = W - pad.l - pad.r;
  const innerH = H - pad.t - pad.b;
  const step = points.length > 1 ? innerW / (points.length - 1) : 0;
  const x = (i: number) => pad.l + (points.length > 1 ? i * step : innerW / 2);
  const yDepth = (d: number) => pad.t + innerH - (Math.min(d, 5) / 5) * innerH;
  const yScore = (s: number) => pad.t + innerH - (s / 100) * innerH;
  const depthPath = points
    .map((p, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${yDepth(p.depth ?? 0).toFixed(1)}`)
    .join(" ");
  const scorePath = points
    .filter((p) => p.score != null)
    .map((p, i) => {
      const idx = points.indexOf(p);
      return `${i === 0 ? "M" : "L"}${x(idx).toFixed(1)},${yScore(p.score ?? 0).toFixed(1)}`;
    })
    .join(" ");

  return (
    <Card>
      <CardHeader className="pb-3">
        <SectionHeading
          eyebrow={t("eyebrows.adaptivity")}
          icon={<TrendingUp className="size-4" aria-hidden />}
          title={t("interviews.report.depthTrajectory")}
          description={t("interviews.report.depthTrajectoryDescription")}
        />
      </CardHeader>
      <CardContent>
        <figure>
          <svg
            viewBox={`0 0 ${W} ${H}`}
            className="h-auto w-full"
            role="img"
            aria-label={t("interviews.report.depthTrajectoryAria", { count: points.length })}
          >
            {/* gridlines at depth levels */}
            {[1, 2, 3, 4, 5].map((lvl) => (
              <line
                key={lvl}
                x1={pad.l}
                x2={W - pad.r}
                y1={yDepth(lvl)}
                y2={yDepth(lvl)}
                stroke="currentColor"
                strokeOpacity={0.08}
              />
            ))}
            <path d={depthPath} fill="none" strokeWidth={2} strokeLinecap="round" className="text-primary" stroke="currentColor" opacity={0.55} />
            {scorePath && (
              <path d={scorePath} fill="none" strokeWidth={2} strokeDasharray="1 4" strokeLinecap="round" className="text-success" stroke="currentColor" />
            )}
            {points.map((p, i) => (
              <g key={i}>
                <circle cx={x(i)} cy={yDepth(p.depth ?? 0)} r={3.5} className="fill-primary" />
                {p.score != null && (
                  <circle
                    cx={x(i)}
                    cy={yScore(p.score)}
                    r={3}
                    className={cn(
                      p.score >= 60 ? "fill-success" : p.score >= 40 ? "fill-warning" : "fill-destructive"
                    )}
                  >
                    <title>{`Q${i + 1}${p.question ? ` · ${p.question}` : ""}: depth ${p.depth ?? "?"} of 5, score ${
                      p.score != null ? p.score : "not graded"
                    }`}</title>
                  </circle>
                )}
                <text x={x(i)} y={H - 6} textAnchor="middle" className="fill-muted-foreground" fontSize={9}>
                  Q{i + 1}
                </text>
              </g>
            ))}
          </svg>
          <figcaption className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-2xs text-muted-foreground">
            <span className="flex items-center gap-1.5">
              <span className="size-2 rounded-full bg-primary" aria-hidden />{" "}
              {t("interviews.report.legendDepth")}
            </span>
            <span className="flex items-center gap-1.5">
              <span className="size-2 rounded-full bg-success" aria-hidden />{" "}
              {t("interviews.report.legendScore")}
            </span>
            {points.some((p) => p.question) && (
              <span>{t("interviews.report.hoverDots")}</span>
            )}
          </figcaption>
        </figure>
      </CardContent>
    </Card>
  );
}
