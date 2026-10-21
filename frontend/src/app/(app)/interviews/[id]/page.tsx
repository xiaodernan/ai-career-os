"use client";

import * as React from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  ArrowRight,
  Check,
  ChevronRight,
  Flag,
  Gauge,
  ListChecks,
  Lightbulb,
  Quote,
  Send,
  Sparkles,
  ThumbsDown,
  ThumbsUp,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { ConfirmDialog } from "@/components/common/confirm-dialog";
import dynamic from "next/dynamic";
import { AIBadge } from "@/components/ai/ai-badge";
import { ProcessingSteps } from "@/components/ai/processing-steps";
import { useInterviewOpening, useSubmitInterviewAnswer, useFinalizeInterview } from "@/lib/hooks/actions";
import { useInterviewSession } from "@/lib/hooks/resources";
import { depthLabel, depthLevel, titleCase } from "@/lib/format";
import { useLocale } from "@/lib/i18n/locale-context";
import type { AnswerResponse } from "@/lib/hooks/actions";
import type { InterviewQuestion } from "@/lib/api/types";

/* Code-split, not a static import: the react-markdown stack is only needed
 * once an answer or transcript renders, so it stays out of the page's first load. */
const StreamingText = dynamic(() =>
  import("@/components/ai/streaming-text").then((m) => m.StreamingText)
);


export default function InterviewRunnerPage() {
  const params = useParams<{ id: string }>();
  const { t } = useLocale();
  const id = params?.id ?? null;
  const router = useRouter();

  const session = useInterviewSession(id);
  const opening = useInterviewOpening(id ?? "");
  const submit = useSubmitInterviewAnswer(id ?? "");
  const finalize = useFinalizeInterview(id ?? "");

  const [question, setQuestion] = React.useState<{
    text: string;
    topic?: string;
    kind?: string;
    difficulty?: number;
  } | null>(null);
  const [answer, setAnswer] = React.useState("");
  const [evaluation, setEvaluation] = React.useState<AnswerResponse["evaluation"] | null>(null);
  const [pendingNext, setPendingNext] = React.useState<InterviewQuestion | null>(null);
  const [turns, setTurns] = React.useState<{ question: string; answer: string; score?: number }[]>([]);
  const [confirmFinish, setConfirmFinish] = React.useState(false);
  const openingFired = React.useRef(false);

  const busy = opening.isPending || submit.isPending;
  const data = session.data;
  const completed = data?.status === "completed" || data?.status === "abandoned";

  // Seed from the server's current question; request the opening once when the
  // session is active but hasn't asked anything yet.
  React.useEffect(() => {
    if (!data || question || completed) return;
    if (data.currentQuestion?.text) {
      setQuestion(data.currentQuestion);
      return;
    }
    if (!openingFired.current) {
      openingFired.current = true;
      opening.mutate(undefined, {
        onSuccess: (res) => {
          if (res.question) {
            setQuestion({
              text: res.question.text,
              topic: res.question.topic,
              kind: res.question.kind,
              difficulty: res.question.difficulty,
            });
          }
        },
      });
    }
  }, [data, question, completed, opening]);

  if (session.isPending) {
    return (
      <div className="mx-auto max-w-3xl space-y-6">
        <Skeleton className="h-4 w-40" />
        <Skeleton className="h-40 rounded-xl" />
        <Skeleton className="h-24 rounded-xl" />
        <span className="sr-only">{t("interviews.detail.loading")}</span>
      </div>
    );
  }

  if (session.isError || !data) {
    return (
      <div className="mx-auto max-w-3xl space-y-6">
        <BackLink />
        <Card>
          <CardContent>
            {session.isError && (session.error as { isNotFound?: boolean })?.isNotFound ? (
              <EmptyState
                icon={<Sparkles aria-hidden />}
                title={t("interviews.detail.missing")}
                description={t("interviews.detail.missingDescription")}
                action={
                  <Button variant="ai" size="sm" asChild>
                    <Link href="/interviews">{t("interviews.detail.allInterviews")}</Link>
                  </Button>
                }
              />
            ) : (
              <ErrorState
                title={t("interviews.detail.loadFailed")}
                error={session.error}
                onRetry={() => void session.refetch()}
                retrying={session.isFetching}
              />
            )}
          </CardContent>
        </Card>
      </div>
    );
  }

  if (completed) {
    return (
      <div className="mx-auto max-w-3xl space-y-6">
        <BackLink />
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-10 text-center">
            <span className="flex size-11 items-center justify-center rounded-xl bg-success/10 text-success">
              <Check className="size-5" aria-hidden />
            </span>
            <h2 className="text-base font-semibold">
              {data.status === "completed" ? "This interview is finished" : "This session was abandoned"}
            </h2>
            <p className="max-w-sm text-sm text-muted-foreground">
              {t("interviews.detail.reportReady")}
            </p>
            <Button variant="ai" size="sm" asChild>
              <Link href={`/interviews/${data.id}/report`}>
                {t("interviews.detail.openReport")}
                <ArrowRight aria-hidden />
              </Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const sendAnswer = () => {
    const trimmed = answer.trim();
    if (!trimmed || !question || busy) return;
    submit.mutate(trimmed, {
      onSuccess: (res) => {
        setTurns((prev) => [...prev, { question: question.text, answer: trimmed, score: res.evaluation.score }]);
        setEvaluation(res.evaluation);
        setPendingNext(res.next);
        setAnswer("");
      },
    });
  };

  const continueNext = () => {
    if (!pendingNext) {
      finish();
      return;
    }
    setQuestion({
      text: pendingNext.text,
      topic: pendingNext.topic,
      kind: pendingNext.kind,
      difficulty: pendingNext.difficulty,
    });
    setEvaluation(null);
    setPendingNext(null);
  };

  const finish = () =>
    finalize.mutate(undefined, {
      onSuccess: () => router.push(`/interviews/${data.id}/report`),
    });

  const showingEvaluation = evaluation != null;

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <BackLink />

      {/* Session header */}
      <div className="flex flex-wrap items-center gap-2">
        <h1 className="font-serif text-display-sm font-medium">
          {titleCase(data.mode)} interview
        </h1>
        {(data.jobTitle || data.companyName) && (
          <span className="text-sm text-muted-foreground">
            · {data.companyName ?? ""} {data.jobTitle ? `— ${data.jobTitle}` : ""}
          </span>
        )}
        >{t("interviews.detail.question", {
              number: turns.length + (showingEvaluation ? 0 : 1),
            })}</Badge>
        {typeof (question?.difficulty ?? data.difficulty) === "number" && (
          <DifficultyMeter value={question?.difficulty ?? data.difficulty!} />
        )}
      </div>

      {/* Question / evaluation */}
      {!showingEvaluation && question && (
        <Card className="animate-fade-up">
          <CardHeader className="pb-2">
            <div className="flex items-center gap-2">
              {question.kind === "followup" ? (
                <Badge variant="ai" className="text-2xs font-normal">
                  {t("interviews.detail.followUp")}
                </Badge>
              ) : question.kind === "next_topic" ? (
                <Badge variant="secondary" className="text-2xs font-normal">
                  {t("interviews.detail.newTopic")}
                </Badge>
              ) : (
                <Badge variant="outline" className="text-2xs font-normal">
                  {t("interviews.detail.opening")}
                </Badge>
              )}
              {question.topic && (
                <span className="text-xs text-muted-foreground">{question.topic}</span>
              )}
            </div>
            <CardTitle className="pt-1 text-base leading-snug font-medium">{question.text}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <Textarea
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              placeholder={t("interviews.detail.answerPlaceholder")}
              rows={5}
              aria-label={t("interviews.detail.answerLabel")}
              onKeyDown={(e) => {
                if (e.key === "Enter" && (e.metaKey || e.ctrlKey) && answer.trim()) {
                  e.preventDefault();
                  sendAnswer();
                }
              }}
            />
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-2xs text-muted-foreground">
                Ctrl+Enter to submit · the agent evaluates before the next question
              </p>
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setConfirmFinish(true)}
                  disabled={submit.isPending}
                >
                  <Flag aria-hidden />
                  {t("interviews.detail.finishAndReport")}
                </Button>
                <Button
                  variant="ai"
                  size="sm"
                  disabled={!answer.trim()}
                  loading={submit.isPending}
                  onClick={sendAnswer}
                >
                  <Send aria-hidden />
                  {t("interviews.detail.submitAnswer")}
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {busy && !showingEvaluation && (
        <ProcessingSteps
          steps={[
            { id: "eval", label: "Evaluating your answer against your real experience", status: "active" },
            { id: "next", label: "Deciding: follow deeper or move topics", status: "pending" },
          ]}
        />
      )}

      {showingEvaluation && (
        <EvaluationPanel
          evaluation={evaluation}
          pendingNext={pendingNext}
          onNext={continueNext}
          onFinish={finish}
          finalizing={finalize.isPending}
        />
      )}

      {/* Turns so far */}
      {turns.length > 0 && (
        <details className="group rounded-xl border border-border/70 bg-muted/20">
          <summary className="flex cursor-pointer items-center gap-2 px-4 py-3 text-sm font-medium text-muted-foreground hover:text-foreground focus-visible:ring-[3px] focus-visible:ring-primary/30">
            <ChevronRight className="size-3.5 transition-transform duration-150 group-open:rotate-90" aria-hidden />
            <ListChecks className="size-4" aria-hidden />
            {t("interviews.detail.thisSessionSoFar")}
            <span className="ml-auto text-xs tabular-nums">
              {t("interviews.detail.answered", { count: turns.length })}
            </span>
          </summary>
          <div className="px-4 pb-4">
            <Separator className="mb-3" />
            <ol className="space-y-2">
              {turns.map((t, i) => (
                <li key={i} className="flex items-start gap-3 text-sm">
                  <span className="mt-0.5 w-5 shrink-0 text-right text-xs text-muted-foreground tabular-nums">
                    {i + 1}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="line-clamp-1 text-foreground">{t.question}</p>
                    <p className="line-clamp-1 text-xs text-muted-foreground">{t.answer}</p>
                  </div>
                  {typeof t.score === "number" && (
                    <Badge
                      variant={t.score >= 75 ? "success" : t.score >= 50 ? "warning" : "destructive"}
                      className="shrink-0 tabular-nums"
                    >
                      {Math.round(t.score)}
                    </Badge>
                  )}
                </li>
              ))}
            </ol>
          </div>
        </details>
      )}

      <ConfirmDialog
        open={confirmFinish}
        onOpenChange={setConfirmFinish}
        title={t("interviews.detail.endTitle")}
        description={t("interviews.detail.endDescription")}
        confirmLabel={t("interviews.detail.finishAndScore")}
        loading={finalize.isPending}
        onConfirm={() => {
          setConfirmFinish(false);
          finish();
        }}
      />
    </div>
  );
}

/* ------------------------------- fragments -------------------------------- */

function BackLink() {
  const { t } = useLocale();
  return (
    <Link
      href="/interviews"
      className="-ml-1 inline-flex w-fit items-center gap-1.5 rounded-md px-1 text-sm text-muted-foreground hover:text-foreground focus-visible:ring-[3px] focus-visible:ring-primary/30"
    >
      <ArrowLeft className="size-4" aria-hidden />
      {t("interviews.detail.allInterviews")}
    </Link>
  );
}

function DifficultyMeter({ value }: { value: number }) {
  // depthLevel owns the 0–1 ↔ 1–5 projection; every depth surface shares it.
  const level = depthLevel(value);
  return (
    <span
      className="flex items-center gap-1.5"
      title={`Depth: ${depthLabel(value)}/5`}
      aria-label={`Difficulty level ${level} of 5`}
    >
      <Gauge className="size-3.5 text-muted-foreground" aria-hidden />
      <span className="flex gap-0.5" aria-hidden>
        {Array.from({ length: 5 }).map((_, i) => (
          <span
            key={i}
            className={cn(
              "h-3 w-1 rounded-full transition-colors duration-300",
              i < level ? (level >= 4 ? "bg-warning" : "bg-primary") : "bg-border"
            )}
          />
        ))}
      </span>
      <span className="text-2xs text-muted-foreground">{depthLabel(value)}</span>
    </span>
  );
}

function EvaluationPanel({
  evaluation,
  pendingNext,
  onNext,
  onFinish,
  finalizing,
}: {
  evaluation: AnswerResponse["evaluation"] | null;
  pendingNext: InterviewQuestion | null;
  onNext: () => void;
  onFinish: () => void;
  finalizing: boolean;
}) {
  const { t } = useLocale();
  if (!evaluation) return null;
  const score = evaluation.score;
  return (
    <Card className="animate-fade-up border-primary/25">
      <CardHeader className="pb-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <CardTitle className="flex items-center gap-2 text-base">
            <AIBadge label="evaluator" />
            {t("interviews.detail.answerEvaluation")}
          </CardTitle>
          {typeof score === "number" && (
            <span
              className={cn(
                "text-lg font-semibold tabular-nums",
                score >= 75 ? "text-success" : score >= 50 ? "text-warning" : "text-destructive"
              )}
            >
              {Math.round(score)}
              <span className="text-xs text-muted-foreground">/100</span>
            </span>
          )}
        </div>
        {evaluation.feedback && (
          <CardDescription>{evaluation.feedback}</CardDescription>
        )}
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-3">
          <PointList
            icon={<ThumbsUp className="size-3.5" aria-hidden />}
            title={t("interviews.detail.wentWell")}
            items={evaluation.strengths}
            tone="success"
          />
          <PointList
            icon={<ThumbsDown className="size-3.5" aria-hidden />}
            title={t("interviews.detail.wasWeak")}
            items={evaluation.weaknesses}
            tone="warning"
          />
          <PointList
            icon={<Quote className="size-3.5" aria-hidden />}
            title={t("interviews.detail.missingPoints")}
            items={evaluation.missing}
            tone="muted"
          />
        </div>

        {evaluation.dims.length > 0 && (
          <ul className="flex flex-wrap gap-1.5">
            {evaluation.dims.map((d) => (
              <li key={d.key}>
                <Badge variant="outline" className="text-2xs font-normal">
                  {d.label}: <span className="tabular-nums text-foreground">{Math.round(d.score)}</span>
                </Badge>
              </li>
            ))}
          </ul>
        )}

        {evaluation.betterAnswer && (
          <div className="rounded-lg border border-border/70 bg-muted/30 p-3">
            <p className="mb-1.5 flex items-center gap-1.5 text-2xs font-medium tracking-wide text-muted-foreground uppercase">
              <Lightbulb className="size-3.5" aria-hidden />
              A stronger answer, from your own material
            </p>
            <StreamingText content={evaluation.betterAnswer} className="text-xs" />
          </div>
        )}

        <Separator />
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="text-xs text-muted-foreground">
            {pendingNext
              ? pendingNext.kind === "followup"
                ? t("interviews.detail.wantsDeeper")
                : t("interviews.detail.movingToNextTopic")
              : t("interviews.detail.noFollowUp")}
          </p>
          <div className="flex items-center gap-2">
            {!pendingNext && (
              <Button variant="outline" size="sm" loading={finalizing} onClick={onFinish}>
                <Flag aria-hidden />
                {t("interviews.detail.finishAndReport")}
              </Button>
            )}
            {pendingNext && (
              <>
                <Button variant="ghost" size="sm" onClick={onFinish} disabled={finalizing}>
                  {t("interviews.detail.finishEarly")}
                </Button>
                <Button variant="ai" size="sm" onClick={onNext}>
                  {t("interviews.detail.nextQuestion")}
                  <ArrowRight aria-hidden />
                </Button>
              </>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function PointList({
  icon,
  title,
  items,
  tone,
}: {
  icon: React.ReactNode;
  title: string;
  items: string[];
  tone: "success" | "warning" | "muted";
}) {
  if (!items.length) return null;
  return (
    <div
      className={cn(
        "rounded-lg border p-3",
        tone === "success" && "border-success/25 bg-success/5",
        tone === "warning" && "border-warning/25 bg-warning/5",
        tone === "muted" && "border-border/70 bg-muted/30"
      )}
    >
      <p className="flex items-center gap-1.5 text-2xs font-medium tracking-wide text-muted-foreground uppercase">
        {icon}
        {title}
      </p>
      <ul className="mt-1.5 ml-4 list-disc space-y-1 text-xs">
        {items.slice(0, 5).map((s, i) => (
          <li key={i}>{s}</li>
        ))}
      </ul>
    </div>
  );
}
