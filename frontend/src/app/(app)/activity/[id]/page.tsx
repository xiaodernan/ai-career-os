"use client";

import * as React from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowLeft,
  Braces,
  Coins,
  Cpu,
  Gauge,
  Timer,
  Waypoints,
  Wrench,
  XCircle,
} from "lucide-react";
import { api } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { AgentTimeline } from "@/components/ai/agent-timeline";
import { PageHeader } from "@/components/common/page-header";
import { QueryBoundary } from "@/components/common/query-boundary";
import { LoadingListSkeleton } from "@/components/common/loading-skeletons";
import { normalizeRunTrace, traceTotals, type RunTrace } from "@/lib/activity-trace";
import { cn } from "@/lib/utils";
import { formatDateTime, formatDuration, formatNumber, formatUsd, relativeTime, titleCase } from "@/lib/format";
import { useLocale } from "@/lib/i18n/locale-context";

function statusVariant(status?: string) {
  if (status === "ok" || status === "completed" || status === "succeeded") return "success" as const;
  if (status === "failed" || status === "error") return "destructive" as const;
  return "warning" as const;
}

function Stat({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: React.ReactNode;
}) {
  return (
    <div className="flex items-center gap-2.5">
      <span className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-muted text-muted-foreground">
        {icon}
      </span>
      <div className="min-w-0">
        <p className="text-2xs font-medium tracking-wide text-muted-foreground uppercase">{label}</p>
        <p className="truncate text-sm font-medium tabular-nums">{value}</p>
      </div>
    </div>
  );
}

function TracePanel({ trace }: { trace: RunTrace }) {
  const { t, locale } = useLocale();
  const totals = traceTotals(trace);
  const { run, steps } = trace;

  return (
    <div className="space-y-6">
      <Card>
        <CardContent className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <Stat
            icon={<Waypoints className="size-4" aria-hidden />}
            label={t("activity.detail.steps")}
            value={`${steps.length}${totals.llmCalls ? ` · ${totals.llmCalls} LLM` : ""}`}
          />
          <Stat
            icon={<Wrench className="size-4" aria-hidden />}
            label={t("activity.detail.toolCalls")}
            value={totals.toolCalls}
          />
          <Stat
            icon={<Cpu className="size-4" aria-hidden />}
            label={t("activity.detail.tokens")}
            value={totals.tokens ? formatNumber(totals.tokens) : "—"}
          />
          <Stat
            icon={<Timer className="size-4" aria-hidden />}
            label={t("activity.detail.latency")}
            value={run.latencyMs ? formatDuration(run.latencyMs) : "—"}
          />
        </CardContent>
      </Card>

      {run.error && (
        <div className="flex items-start gap-3 rounded-xl border border-destructive/30 bg-destructive/5 p-4">
          <XCircle className="mt-0.5 size-4 shrink-0 text-destructive" aria-hidden />
          <div className="min-w-0">
            <p className="text-sm font-medium text-destructive">
              {t("activity.detail.thisRunFailed")}
            </p>
            <p className="mt-0.5 font-mono text-xs break-words text-muted-foreground">{run.error}</p>
          </div>
        </div>
      )}

      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <Braces className="size-4 text-muted-foreground" aria-hidden />
              <h2 className="font-serif text-lg font-medium">{t("activity.detail.executionTrace")}</h2>
            </div>
            <p className="text-xs text-muted-foreground">
              {t("activity.detail.traceHint")}
            </p>
          </div>
        </CardHeader>
        <CardContent>
          {steps.length ? (
            <AgentTimeline events={steps} className="gap-1" />
          ) : (
            <p className="text-sm text-muted-foreground">
              {t("activity.detail.noTraceSteps")}
            </p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center gap-2">
            <Coins className="size-4 text-muted-foreground" aria-hidden />
            <h2 className="font-serif text-lg font-medium">{t("activity.detail.attribution")}</h2>
          </div>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <dl className="grid gap-x-6 gap-y-2 sm:grid-cols-2">
            <div className="flex items-center justify-between gap-3 border-b border-border/60 pb-2">
              <dt className="text-muted-foreground">{t("activity.detail.runId")}</dt>
              <dd className="truncate font-mono text-xs">{run.id}</dd>
            </div>
            <div className="flex items-center justify-between gap-3 border-b border-border/60 pb-2">
              <dt className="text-muted-foreground">{t("activity.detail.cost")}</dt>
              <dd className="tabular-nums">{totals.costUsd ? formatUsd(totals.costUsd) : "—"}</dd>
            </div>
            <div className="flex items-center justify-between gap-3 border-b border-border/60 pb-2">
              <dt className="text-muted-foreground">{t("activity.detail.started")}</dt>
              <dd>{run.startedAt ? `${formatDateTime(run.startedAt, locale)} · ${relativeTime(run.startedAt, locale)}` : "—"}</dd>
            </div>
            <div className="flex items-center justify-between gap-3 border-b border-border/60 pb-2">
              <dt className="text-muted-foreground">{t("activity.detail.finished")}</dt>
              <dd>{run.finishedAt ? relativeTime(run.finishedAt, locale) : "still running"}</dd>
            </div>
            <div className="flex items-center justify-between gap-3 border-b border-border/60 pb-2">
              <dt className="text-muted-foreground">{t("activity.detail.model")}</dt>
              <dd className="truncate font-mono text-xs">{run.model || "—"}</dd>
            </div>
            <div className="flex items-center justify-between gap-3 border-b border-border/60 pb-2">
              <dt className="text-muted-foreground">{t("activity.detail.agent")}</dt>
              <dd>{run.agent ?? "career"}</dd>
            </div>
          </dl>
          {run.conversationId && (
            <Button variant="outline" size="sm" asChild className="self-start">
              <Link href={`/copilot?c=${run.conversationId}`}>
                {t("activity.detail.openConversation")}
                <ArrowLeft className="rotate-180" aria-hidden />
              </Link>
            </Button>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default function ActivityRunPage() {
  const params = useParams<{ id: string }>();
  const { t } = useLocale();
  const id = params?.id ?? null;

  const query = useQuery({
    queryKey: ["activity", "run-detail", id],
    enabled: Boolean(id),
    queryFn: async (): Promise<RunTrace> =>
      normalizeRunTrace(await api.get<unknown>(endpoints.activityRun(id!))),
  });

  const run = query.data?.run;

  return (
    <div className="space-y-6">
      <PageHeader
        title={
          <span className="flex flex-wrap items-center gap-3">
            <AgentRunTitle run={run} />
            {run?.status && (
              <Badge variant={statusVariant(run.status)} className="capitalize">
                {titleCase(run.status)}
              </Badge>
            )}
          </span>
        }
        description={
          run
            ? `${run.agent ?? "career"} · ${run.trigger ?? "run"} — every step the orchestrator persisted for this run.`
            : t("activity.detail.debugView")
        }
        actions={
          <Button variant="outline" size="sm" asChild>
            <Link href="/activity">
              <ArrowLeft aria-hidden />
              {t("activity.detail.allActivity")}
            </Link>
          </Button>
        }
      />

      <QueryBoundary
        query={query}
        boxed={false}
        skeleton={
          <div className="space-y-4">
            <Card>
              <CardContent>
                <LoadingListSkeleton rows={2} />
              </CardContent>
            </Card>
            <Card>
              <CardContent>
                <LoadingListSkeleton rows={6} />
              </CardContent>
            </Card>
          </div>
        }
        empty={{
          icon: <Gauge aria-hidden />,
          title: t("activity.detail.runGone"),
          description:
            t("activity.detail.runGoneDescription"),
          action: (
            <Button variant="outline" size="sm" asChild>
              <Link href="/activity">{t("activity.detail.backToActivity")}</Link>
            </Button>
          ),
        }}
      >
        {(trace) => (
          <>
            <Separator />
            <TracePanel trace={trace} />
          </>
        )}
      </QueryBoundary>
    </div>
  );
}

function AgentRunTitle({ run }: { run?: RunTrace["run"] }) {
  const { t } = useLocale();
  return (
    <span className={cn("font-serif text-display-md")}>
      {run?.trigger ? `${titleCase(run.trigger)} run` : t("activity.detail.agentRun")}
    </span>
  );
}
