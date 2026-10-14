"use client";

import * as React from "react";
import {
  ArrowDownRight,
  ArrowUpRight,
  Check,
  GraduationCap,
  Minus,
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
      <Card>
        <CardHeader>
          <CardTitle>Growth report</CardTitle>
          <CardDescription>
            One call composes readiness, the gap behind it, the market&apos;s salary band, a
            phased learning plan, and what moved since your last run.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form className="flex flex-wrap items-end gap-3" onSubmit={submit}>
            <div className="min-w-0 flex-1 basis-64 space-y-2">
              <Label htmlFor="growth-role">Target role</Label>
              <Input
                id="growth-role"
                value={targetRole}
                onChange={(e) => setTargetRole(e.target.value)}
                placeholder="e.g. Senior Backend Engineer (Java)"
                autoComplete="off"
              />
            </div>
            <div className="min-w-0 flex-1 basis-44 space-y-2">
              <Label htmlFor="growth-location">Location (optional)</Label>
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
              Analyze
            </Button>
          </form>
          {targetRole.trim().length > 0 && targetRole.trim().length < 10 && (
            <p className="mt-2 text-xs text-muted-foreground">
              Name the role fully — the analyzer needs at least 10 characters to target it.
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
          title="No report yet"
          description="Name the role you're aiming at and run the analyzer — the report is built from your resume's evidence, not from a form you fill in."
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
              <div className="grid grid-cols-3 gap-2 text-center text-sm">
                <Count label="Covered" value={readiness.coveredCount ?? 0} />
                <Count label="Partial" value={gap?.partialCount ?? 0} />
                <Count label="Open" value={readiness.gapCount ?? 0} />
              </div>
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
                <CardTitle>Salary band</CardTitle>
                <CardDescription>
                  {salary.sampleSize ?? 0} matched postings
                  {salary.location ? ` in ${salary.location}` : ""}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
                  {(["p25", "p50", "p75"] as const).map((k) => (
                    <div key={k}>
                      <p className="text-xs text-muted-foreground uppercase">{k}</p>
                      <p className="text-lg font-medium tabular-nums">
                        {formatSalary(
                          salary.percentiles?.[k],
                          salary.percentiles?.[k],
                          salary.currency,
                        )}
                      </p>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader>
              <CardTitle>Learning plan</CardTitle>
              <CardDescription>Foundation first, then the role&apos;s core, then the applied.</CardDescription>
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
                  Nothing to study — every expected skill has evidence behind it.
                </p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Progress</CardTitle>
              <CardDescription>
                {progress?.baseline
                  ? "First report for this role — the next run diffs against this one."
                  : "Against your previous report for this role."}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ProgressLines progress={progress} />
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}

/** One covered/partial/gap split, as one bar. */
function CoverageBar({ coverage }: { coverage: number }) {
  const pct = Math.round(Math.max(0, Math.min(1, coverage)) * 100);
  return (
    <div>
      <div className="flex items-baseline justify-between">
        <span className="text-sm text-muted-foreground">Coverage</span>
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

function Count({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border border-border/50 p-2">
      <p className="text-lg font-medium tabular-nums">{value}</p>
      <p className="text-xs text-muted-foreground">{label}</p>
    </div>
  );
}

/**
 * The progress block's rows. On the baseline run there is nothing to compare — the
 * engine still answers the shape, with empty lists — so the card says what it will
 * say next time instead of rendering three empty groups.
 */
function ProgressLines({ progress }: { progress?: GrowthReport["progress"] }) {
  if (!progress) return null;
  const groups = [
    { label: "Closed", skills: progress.closed ?? [], icon: Check, tone: "text-success" },
    { label: "Improved", skills: progress.improved ?? [], icon: ArrowUpRight, tone: "text-primary" },
    { label: "Regressed", skills: progress.regressed ?? [], icon: ArrowDownRight, tone: "text-destructive" },
  ];
  const any = groups.some((g) => g.skills.length > 0);
  return (
    <div className="space-y-3">
      <div className="flex items-baseline gap-2">
        <span className="text-sm text-muted-foreground">Coverage</span>
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
            <div key={g.label}>
              <p className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
                {g.label}
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
            No skill changed state since the last report
            {(progress.stillOpen ?? []).length > 0
              ? ` — ${(progress.stillOpen ?? []).length} still open.`
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
