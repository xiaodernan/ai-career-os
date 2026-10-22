"use client";

import * as React from "react";
import Link from "next/link";
import { ArrowRight, BadgeDollarSign, Briefcase, CalendarClock, FileText, ListOrdered, Scale, Sparkles, Target } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { MatchRing } from "@/components/ai/match-ring";
import { SkillChips, DimensionBars } from "@/components/common/skill-chips";
import { DiffView } from "@/components/common/diff-view";
import { EvidenceList } from "@/components/ai/evidence-list";
import { BarChart } from "@/components/common/bar-chart";
import dynamic from "next/dynamic";
import { CopyButton } from "@/components/common/export-buttons";
import { JobCard } from "@/components/jobs/job-card";
import { matchDimensionLabel } from "@/lib/dimensions";
import {
  list,
  normalizeJob,
  normalizeMatch,
  normalizePage,
  normalizeTailor,
  num,
  pick,
  str,
  coverLetterText,
} from "@/lib/api/normalize";
import { formatSalary } from "@/lib/format";
import { useLocale } from "@/lib/i18n/locale-context";
import type { CopilotArtifact, Evidence } from "@/lib/api/types";

/* Code-split, not a static import: the react-markdown stack is only needed
 * once an artifact with prose renders, so it stays out of the copilot's first load. */
const StreamingText = dynamic(() =>
  import("@/components/ai/streaming-text").then((m) => m.StreamingText)
);

/**
 * ArtifactCard — Copilot answers carry structured artifacts. Each type gets
 * the same renderer the first-class pages use, so a match inside chat looks
 * like a match on the job page (ring + evidence, not a blob of JSON).
 */
export function ArtifactCard({ artifact }: { artifact: CopilotArtifact }) {
  const data = artifact.data;
  switch (artifact.type) {
    case "match":
      return <MatchArtifact data={data} />;
    case "job_list":
      return <JobListArtifact data={data} />;
    case "tailored_resume":
      return <TailorArtifact data={data} />;
    case "cover_letter":
      return <CoverLetterArtifact data={data} />;
    case "interview_session":
      return <InterviewArtifact data={data} />;
    case "gap_report":
      return <GapReportArtifact data={data} />;
    case "salary_band":
      return <SalaryBandArtifact data={data} />;
    case "offer_comparison":
      return <OfferComparisonArtifact data={data} />;
    case "learning_priority":
      return <LearningPriorityArtifact data={data} />;
    default:
      return null; // unknown types are ignored — never rendered as raw JSON
  }
}

/* --------------------------------- match --------------------------------- */

function MatchArtifact({ data }: { data?: unknown }) {
  const { t } = useLocale();
  const match = normalizeMatch(pick(data, "match") ?? data);
  if (!match) return null;
  const evidence: Evidence[] = match.evidence ?? [];
  const dims =
    match.dimensions?.length
      ? match.dimensions
      : [
          { key: "technical", score: match.technical },
          { key: "experience", score: match.experience },
          { key: "projects", score: match.projects },
          { key: "education", score: match.education },
        ]
          .filter((d) => d.score != null)
          .map((d) => ({ ...d, label: matchDimensionLabel(t, d.key) }));
  return (
    <Card className="border-primary/25">
      <CardContent className="flex flex-col gap-3">
        <div className="flex items-center gap-3">
          <MatchRing value={match.overall} size={56} thickness={5} label={t("artifacts.matchRing")} />
          <div className="min-w-0">
            <p className="text-2xs font-medium tracking-wide text-muted-foreground uppercase">
              {t("artifacts.match")}
            </p>
            {match.reasoning && <p className="mt-0.5 text-sm">{match.reasoning}</p>}
          </div>
        </div>
        <DimensionBars dimensions={dims} dense />
        <SkillChips matched={match.matchedSkills} missing={match.missingSkills} showLabels />
        {evidence.length > 0 && (
          <EvidenceList
            items={evidence}
            limit={2}
            dense
            hrefFor={(e) => (e.source?.docId ? `/knowledge?src=${e.source.docId}` : undefined)}
          />
        )}
        {match.jobId && (
          <Button variant="outline" size="sm" asChild className="self-start">
            <Link href={`/jobs/${match.jobId}`}>
              {t("artifacts.openJob")}
              <ArrowRight aria-hidden />
            </Link>
          </Button>
        )}
      </CardContent>
    </Card>
  );
}

/* -------------------------------- job_list -------------------------------- */

function JobListArtifact({ data }: { data?: unknown }) {
  const { t } = useLocale();
  const page = normalizePage(data, normalizeJob);
  const jobs = page.items.length ? page.items : normalizePage(pick(data, "jobs") ?? data, normalizeJob).items;
  if (!jobs.length) return null;
  return (
    <Card className="border-primary/25">
      <CardContent className="space-y-2.5">
        <p className="flex items-center gap-1.5 text-2xs font-medium tracking-wide text-muted-foreground uppercase">
          <Briefcase className="size-3.5" aria-hidden />
          {t("artifacts.matchingRoles", { count: jobs.length })}
        </p>
        <ul className="space-y-2">
          {jobs.slice(0, 5).map((j) => (
            <li key={j.id}>
              <JobCard job={j} dense showSave={false} />
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}

/* ----------------------------- tailored_resume ----------------------------- */

function TailorArtifact({ data }: { data?: unknown }) {
  const { t } = useLocale();
  const tailor = normalizeTailor(data);
  const diff = tailor.diff;
  const text = tailor.tailored?.markdown;
  if (!diff && !text) return null;
  return (
    <Card className="border-primary/25">
      <CardContent className="space-y-3">
        <p className="flex items-center gap-1.5 text-2xs font-medium tracking-wide text-muted-foreground uppercase">
          <Sparkles className="size-3.5" aria-hidden />
          {t("artifacts.tailoredResume")}
        </p>
        {diff && (diff.accepted.length > 0 || diff.rejected.length > 0) ? (
          <DiffView accepted={diff.accepted} rejected={diff.rejected} notes={tailor.notes} />
        ) : text ? (
          <StreamingText content={text} className="max-h-72 overflow-y-auto text-xs" />
        ) : null}
        {tailor.evidence && tailor.evidence.length > 0 && (
          <EvidenceList items={tailor.evidence} limit={2} dense />
        )}
        {text && <CopyButton text={text} label={t("artifacts.copyDraft")} />}
      </CardContent>
    </Card>
  );
}

/* ------------------------------- cover_letter ------------------------------ */

function CoverLetterArtifact({ data }: { data?: unknown }) {
  const { t } = useLocale();
  const text = coverLetterText(data);
  if (!text) return null;
  return (
    <Card className="border-primary/25">
      <CardContent className="space-y-3">
        <p className="flex items-center gap-1.5 text-2xs font-medium tracking-wide text-muted-foreground uppercase">
          <FileText className="size-3.5" aria-hidden />
          {t("artifacts.coverLetter")}
        </p>
        <StreamingText content={text} className="max-h-80 overflow-y-auto" />
        <CopyButton text={text} label={t("artifacts.copyLetter")} />
      </CardContent>
    </Card>
  );
}

/* ----------------------------- interview_session ---------------------------- */

function InterviewArtifact({ data }: { data?: unknown }) {
  const { t } = useLocale();
  const id = str(data, "sessionId", "session_id", "id") ?? str(pick(data, "session"), "id");
  if (!id) return null;
  return (
    <Card className="border-primary/25">
      <CardContent className="flex flex-wrap items-center gap-3">
        <span className="flex size-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
          <CalendarClock className="size-4.5" aria-hidden />
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium">{t("artifacts.interview")}</p>
          <p className="text-xs text-muted-foreground">
            {t("artifacts.interviewPrepared")}
          </p>
        </div>
        <Button variant="ai" size="sm" asChild>
          <Link href={`/interviews/${id}`}>
            {t("artifacts.start")}
            <ArrowRight aria-hidden />
          </Link>
        </Button>
      </CardContent>
    </Card>
  );
}

/* --------------------------------- gaps ---------------------------------- */

/* `skill_gap` was a case here, with this renderer under it, until #145a measured that no path through
 * `_collect_artifacts` ever appends that type: the card could not be reached, while the job page's own
 * gap panel -- fed by the persisted `skillGaps` column, which #126 gave a real producer -- is where
 * gaps actually show. The gate that compares this switch with the types the orchestrator writes is
 * what would catch its return. */

/* --------------------------- the growth engines --------------------------- */

/*
 * The four deterministic growth engines (Epics 10.x, 12.x) answer inside the
 * conversation now, so the copilot can say "you are 42% ready for this role"
 * and the user sees the same card the growth page would draw.
 *
 * Each renderer reads the engine's own shape and draws it with the same
 * components the first-class pages use -- a bar chart for the numbers, a chip
 * for a skill -- so an answer in chat looks like the page it came from.
 */

function GrowthArtifact({
  title,
  eyebrowKey,
  icon,
  children,
}: {
  title?: string;
  /** The translation key for the card's eyebrow -- the name of the answer. */
  eyebrowKey: string;
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  const { t } = useLocale();
  return (
    <Card className="border-primary/25">
      <CardContent className="space-y-3">
        <p className="flex items-center gap-1.5 text-2xs font-medium tracking-wide text-muted-foreground uppercase">
          {icon}
          {t(eyebrowKey)}
        </p>
        {title && <p className="text-sm font-medium">{title}</p>}
        {children}
      </CardContent>
    </Card>
  );
}

function GapReportArtifact({ data }: { data?: unknown }) {
  const { t } = useLocale();
  const report = pick(data, "gap") ?? data;
  const targetRole = str(report, "targetRole", "target_role");
  const coverage = num(report, "coverage");
  const gaps = list(report, "gaps");
  if (coverage == null && !gaps.length) return null;
  return (
    <GrowthArtifact
      eyebrowKey="artifacts.gapReport"
      title={targetRole}
      icon={<Target className="size-3.5" aria-hidden />}
    >
      {coverage != null && (
        <BarChart
          data={[{ label: t("artifacts.coverage"), value: Math.round(coverage * 100), tone: "primary" }]}
          max={100}
          valueFormat={(v) => `${v}%`}
        />
      )}
      {gaps.length > 0 && (
        <ul className="flex flex-wrap gap-1.5">
          {gaps.map((g, i) => (
            <li key={i}>
              {/* Rows are `{skill, importance, category}` dicts: never stringify one. */}
              <Badge variant="outline">{str(g, "skill") ?? "—"}</Badge>
            </li>
          ))}
        </ul>
      )}
    </GrowthArtifact>
  );
}

function SalaryBandArtifact({ data }: { data?: unknown }) {
  const report = pick(data, "salary") ?? data;
  const percentiles = pick(report, "percentiles");
  const rows = ["p25", "p50", "p75"]
    .map((k) => ({ key: k, value: num(percentiles, k) }))
    .filter((r): r is { key: string; value: number } => r.value != null);
  if (!rows.length) return null;
  const currency = str(report, "currency") ?? "CNY";
  return (
    <GrowthArtifact
      eyebrowKey="artifacts.salaryBand"
      title={str(report, "role") ?? undefined}
      icon={<BadgeDollarSign className="size-3.5" aria-hidden />}
    >
      <BarChart
        data={rows.map((r) => ({
          label: r.key,
          value: r.value,
          tone: r.key === "p50" ? ("primary" as const) : ("muted" as const),
        }))}
        valueFormat={(v) => formatSalary(v, v, currency) ?? "—"}
      />
    </GrowthArtifact>
  );
}

function OfferComparisonArtifact({ data }: { data?: unknown }) {
  const report = pick(data, "comparison") ?? data;
  const rows = list(report, "rows");
  if (!rows.length) return null;
  return (
    <GrowthArtifact
      eyebrowKey="artifacts.offerComparison"
      icon={<Scale className="size-3.5" aria-hidden />}
    >
      <BarChart
        data={rows.map((row, i) => ({
          label: str(row, "label") ?? `Offer ${i + 1}`,
          value: num(row, "totalComp", "total_comp") ?? 0,
          tone: "primary" as const,
        }))}
        valueFormat={(v) => formatSalary(v, v, str(report, "currency") ?? "CNY") ?? "—"}
      />
    </GrowthArtifact>
  );
}

function LearningPriorityArtifact({ data }: { data?: unknown }) {
  const report = pick(data, "priority") ?? data;
  const rows = list(report, "prioritizedGaps");
  if (!rows.length) return null;
  return (
    <GrowthArtifact
      eyebrowKey="artifacts.learningPriority"
      icon={<ListOrdered className="size-3.5" aria-hidden />}
    >
      <ol className="space-y-1.5">
        {rows.map((row, i) => (
          <li key={i} className="flex items-center justify-between gap-2 text-sm">
            <span className="min-w-0 truncate">{str(row, "skill") ?? "—"}</span>
            <Badge variant="secondary" className="shrink-0 text-2xs">
              {str(row, "priority") ?? "—"}
            </Badge>
          </li>
        ))}
      </ol>
    </GrowthArtifact>
  );
}

