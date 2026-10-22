"use client";

import * as React from "react";
import {
  ArrowDownRight,
  ArrowUpRight,
  Check,
  GraduationCap,
  Minus,
  Plus,
  ScanSearch,
  Target,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/common/empty-state";
import { BarChart, ShareChart } from "@/components/common/bar-chart";
import { GrowthEnginesPanel } from "@/components/growth/growth-engines-panel";
import { PageHeader } from "@/components/common/page-header";
import { useLocale } from "@/lib/i18n/locale-context";
import { useGrowthReport } from "@/lib/hooks/actions";
import { formatSalary } from "@/lib/format";
import type { GrowthReport } from "@/lib/api/types";

/**
 * The growth page (roadmap 10.3): a target role in, one report out — readiness
 * verdict, the coverage split behind it, the salary band the postings pay, the
 * phased learning plan, and what moved since the last run.
 *
 * The report is computed per call, not stored (10.4 will persist it), so the panel
 * keeps its own previous answer in state and offers it back as `previous` — that is
 * the whole progress story until the server-side plan exists. Reload wipes it, and
 * the progress block says "baseline" rather than pretending to remember.
 */

const VERDICT_VARIANT: Record<string, "success" | "ai" | "warning" | "destructive"> = {
  ready: "success",
  borderline: "ai",
  not_ready: "warning",
};

export default function GrowthPage() {
  const { t } = useLocale();
  const [targetRole, setTargetRole] = React.useState("");
  const [location, setLocation] = React.useState("");
  // One report in state, doing two jobs: it is what renders, and its gap block is
  // the `previous` the next run's progress diff reads — nothing else carries over.
  const [report, setReport] = React.useState<GrowthReport | null>(null);
  const build = useGrowthReport();

  const submit = React.useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      const role = targetRole.trim();
      if (role.length < 10 || build.isPending) return;
      build.mutate(
        {
          targetRole: role,
          location: location.trim() || undefined,
          // The gap block names the role it was built for — that is the diff anchor.
          previous: report?.gap?.targetRole === role ? report.gap : undefined,
        },
        { onSuccess: (out) => setReport(out) },
      );
    },
    [targetRole, location, report, build],
  );

  const gap = report?.gap;
  const readiness = report?.readiness;
  const salary = report?.salary;
  const plan = report?.learningPlan;
  const progress = report?.progress;

  return (
    <div className="space-y-4">
      <PageHeader
        title={t("growth.title")}
        description={t("growth.description")}
      />
      <Card>
        <CardHeader>
          <CardTitle>{t("growth.buildReport")}</CardTitle>
          <CardDescription>
            {t("growth.buildReportDescription")}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form className="flex flex-wrap items-end gap-3" onSubmit={submit}>
            <div className="min-w-0 flex-1 basis-64 space-y-2">
              <Label htmlFor="growth-role">{t("growth.targetRole")}</Label>
              <Input
                id="growth-role"
                value={targetRole}
                onChange={(e) => setTargetRole(e.target.value)}
                placeholder="e.g. Senior Backend Engineer (Java)"
                autoComplete="off"
              />
            </div>
            <div className="min-w-0 flex-1 basis-44 space-y-2">
              <Label htmlFor="growth-location">{t("growth.location")}</Label>
              <Input
                id="growth-location"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                placeholder="e.g. Shanghai"
                autoComplete="off"
              />
            </div>
            <Button
              type="submit"
              variant="ai"
              loading={build.isPending}
              disabled={targetRole.trim().length < 10}
            >
              <ScanSearch aria-hidden />
              {t("growth.analyze")}
            </Button>
          </form>
          {targetRole.trim().length > 0 && targetRole.trim().length < 10 && (
            <p className="mt-2 text-xs text-muted-foreground">
              {t("growth.roleTooShort")}
            </p>
          )}
        </CardContent>
      </Card>

      {build.isPending && (
        <div className="space-y-4">
          <Skeleton className="h-28 rounded-xl" />
          <Skeleton className="h-40 rounded-xl" />
          <Skeleton className="h-56 rounded-xl" />
        </div>
      )}

      {!build.isPending && !report && (
        <EmptyState
          title={t("growth.noReport")}
          description={t("growth.noReportDescription")}
          icon={<Target aria-hidden />}
        />
      )}

      {report && readiness && (
        <>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between gap-3">
              <div className="min-w-0">
                <CardTitle className="truncate">{readiness.targetRole ?? targetRole}</CardTitle>
                <CardDescription>
                  {readiness.coveredCount ?? 0} covered · {gap?.partialCount ?? 0} partial ·{" "}
                  {readiness.gapCount ?? 0} open of {gap?.expectedSkillCount ?? 0} expected skills
                </CardDescription>
              </div>
              <Badge
                variant={VERDICT_VARIANT[readiness.verdict ?? ""] ?? "secondary"}
                className="shrink-0 capitalize"
              >
                {(readiness.verdict ?? "unknown").replace("_", " ")}
              </Badge>
            </CardHeader>
            <CardContent className="space-y-3">
              <CoverageBar coverage={gap?.coverage ?? readiness.skillReadiness ?? 0} />
              {/* The same three numbers the cards below carried, drawn as a
                  split: what the profile covers, what it half-covers and
                  what is open is a shape, and a shape reads faster than
                  three numbers side by side. */}
              <ShareChart
                data={[
                  {
                    label: t("growth.covered"),
                    value: readiness.coveredCount ?? 0,
                    tone: "success" as const,
                  },
                  {
                    label: t("growth.partial"),
                    value: gap?.partialCount ?? 0,
                    tone: "warning" as const,
                  },
                  {
                    label: t("growth.open"),
                    value: readiness.gapCount ?? 0,
                    tone: "destructive" as const,
                  },
                ]}
              />
              {(readiness.blockers ?? []).length > 0 && (
                <ul className="space-y-1 text-sm text-destructive">
                  {(readiness.blockers ?? []).map((b) => (
                    <li key={b}>{b}</li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>

          {salary?.percentiles && (salary.percentiles.p50 ?? 0) > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>{t("growth.salaryBand")}</CardTitle>
                <CardDescription>
                  {salary.sampleSize ?? 0} matched postings
                  {salary.location ? ` in ${salary.location}` : ""}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <BarChart
                  data={(["p25", "p50", "p75"] as const).map((k) => ({
                    label: k,
                    value: salary.percentiles?.[k] ?? 0,
                    // The median is the one the negotiation is measured against,
                    // so it carries the accent; the tails are the range around it.
                    tone: k === "p50" ? ("primary" as const) : ("muted" as const),
                  }))}
                  valueFormat={(v) => formatSalary(v, v, salary.currency) ?? "—"}
                />
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader>
              <CardTitle>{t("growth.learningPlan")}</CardTitle>
              <CardDescription>{t("growth.learningPlanDescription")}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {(plan?.phases ?? []).length > 0 ? (
                (plan?.phases ?? []).map((phase) => (
                  <div key={phase.phase} className="space-y-2">
                    <h4 className="flex items-center gap-2 text-xs font-semibold tracking-wide text-muted-foreground uppercase">
                      <GraduationCap className="size-3.5" aria-hidden />
                      {phase.label ?? phase.phase}
                    </h4>
                    <ul className="space-y-1.5">
                      {(phase.items ?? []).map((item) => (
                        <li key={item.topic} className="flex flex-wrap items-baseline gap-2 text-sm">
                          <span className="font-medium">{item.topic}</span>
                          <Badge
                            variant={item.priority === "must" ? "destructive" : "secondary"}
                            className="text-2xs"
                          >
                            {item.priority}
                          </Badge>
                          {item.resource_hint && (
                            <span className="text-xs text-muted-foreground">
                              {item.resource_hint}
                            </span>
                          )}
                          {item.note && (
                            <span className="text-xs text-muted-foreground">{item.note}</span>
                          )}
                        </li>
                      ))}
                    </ul>
                  </div>
                ))
              ) : (
                <p className="text-sm text-muted-foreground">
                  {t("growth.nothingToStudy")}
                </p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>{t("growth.progress")}</CardTitle>
              <CardDescription>
                {progress?.baseline ? t("growth.progressBaseline") : t("growth.progressAgainstPrevious")}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ProgressLines progress={progress} />
            </CardContent>
          </Card>
        </>
      )}

      {/* The granular engines, each on its own (10.1-10.13) — the same ones the
          report above composes, asked one question at a time. */}
      <GrowthEnginesPanel />
    </div>
  );
}

/** One covered/partial/gap split, as one bar. */
function CoverageBar({ coverage }: { coverage: number }) {
  const { t } = useLocale();
  const pct = Math.round(Math.max(0, Math.min(1, coverage)) * 100);
  return (
    <div>
      <div className="flex items-baseline justify-between">
        <span className="text-sm text-muted-foreground">{t("growth.coverage")}</span>
        <span className="text-sm font-medium tabular-nums">{pct}%</span>
      </div>
      <div className="mt-1 h-2 overflow-hidden rounded-full bg-muted">
        <div
          className="h-full rounded-full bg-primary"
          style={{ width: `${pct}%` }}
          role="progressbar"
          aria-valuenow={pct}
          aria-valuemin={0}
          aria-valuemax={100}
        />
      </div>
    </div>
  );
}

/**
 * The progress block's rows. On the baseline run there is nothing to compare — the
 * engine still answers the shape, with empty lists — so the card says what it will
 * say next time instead of rendering a stack of empty groups. Every list the engine
 * answers is one of these groups: a state the diff can name is a state the user is
 * shown, which is what `opened` means (a gap the previous report did not list).
 */
function ProgressLines({ progress }: { progress?: GrowthReport["progress"] }) {
  const { t } = useLocale();
  if (!progress) return null;
  const groups = [
    { labelKey: "growth.skillsClosed", skills: progress.closed ?? [], icon: Check, tone: "text-success" },
    { labelKey: "growth.skillsImproved", skills: progress.improved ?? [], icon: ArrowUpRight, tone: "text-primary" },
    // A skill the previous report did not list at all and the current one calls a
    // gap: the expected set moved under the user, so it is neither closed nor a
    // regression of something they used to cover.
    { labelKey: "growth.skillsOpened", skills: progress.opened ?? [], icon: Plus, tone: "text-warning" },
    { labelKey: "growth.skillsRegressed", skills: progress.regressed ?? [], icon: ArrowDownRight, tone: "text-destructive" },
  ];
  const any = groups.some((g) => g.skills.length > 0);
  return (
    <div className="space-y-3">
      <div className="flex items-baseline gap-2">
        <span className="text-sm text-muted-foreground">{t("growth.coverage")}</span>
        {progress.baseline ? (
          <span className="text-sm font-medium tabular-nums">
            {Math.round((progress.currentCoverage ?? 0) * 100)}%
          </span>
        ) : (
          <span className="flex items-center gap-1 text-sm font-medium tabular-nums">
            <DeltaGlyph delta={progress.delta ?? 0} />
            {Math.round((progress.previousCoverage ?? 0) * 100)}% →{" "}
            {Math.round((progress.currentCoverage ?? 0) * 100)}%
          </span>
        )}
      </div>
      {any ? (
        groups.map((g) =>
          g.skills.length > 0 ? (
            <div key={g.labelKey}>
              <p className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
                {t(g.labelKey)}
              </p>
              <ul className="mt-1 space-y-1">
                {g.skills.map((s) => (
                  <li key={s} className="flex items-center gap-2 text-sm">
                    <g.icon className={`size-3.5 ${g.tone}`} aria-hidden />
                    {s}
                  </li>
                ))}
              </ul>
            </div>
          ) : null,
        )
      ) : (
        !progress.baseline && (
          <p className="text-sm text-muted-foreground">
            {t("growth.noSkillChange")}
            {(progress.stillOpen ?? []).length > 0
              ? ` — ${t("growth.stillOpen", { count: (progress.stillOpen ?? []).length })}`
              : "."}
          </p>
        )
      )}
    </div>
  );
}

function DeltaGlyph({ delta }: { delta: number }) {
  if (delta > 0) return <ArrowUpRight className="size-4 text-success" aria-hidden />;
  if (delta < 0) return <ArrowDownRight className="size-4 text-destructive" aria-hidden />;
  return <Minus className="size-4 text-muted-foreground" aria-hidden />;
}
