"use client";

import * as React from "react";
import Link from "next/link";
import { ArrowRight, Briefcase, CalendarClock, FileText, Layers, Sparkles } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { MatchRing } from "@/components/ai/match-ring";
import { SkillChips, DimensionBars } from "@/components/common/skill-chips";
import { DiffView } from "@/components/common/diff-view";
import { EvidenceList } from "@/components/ai/evidence-list";
import { StreamingText } from "@/components/ai/streaming-text";
import { CopyButton } from "@/components/common/export-buttons";
import { JobCard } from "@/components/jobs/job-card";
import {
  list as listOf,
  normalizeJob,
  normalizeMatch,
  normalizePage,
  normalizeTailor,
  pick,
  str,
  coverLetterText,
} from "@/lib/api/normalize";
import type { CopilotArtifact, Evidence } from "@/lib/api/types";

/**
 * ArtifactCard — Copilot answers carry structured artifacts. Each type gets
 * the same renderer the first-class pages use, so a match inside chat looks
 * like a match on the job page (ring + evidence, not a blob of JSON).
 */
export function ArtifactCard({ artifact }: { artifact: CopilotArtifact }) {
  const data = artifact.data;
  switch (artifact.type) {
    case "match":
      return <MatchArtifact data={data} title={artifact.title} />;
    case "job_list":
      return <JobListArtifact data={data} title={artifact.title} />;
    case "tailored_resume":
      return <TailorArtifact data={data} title={artifact.title} />;
    case "cover_letter":
      return <CoverLetterArtifact data={data} title={artifact.title} />;
    case "interview_session":
      return <InterviewArtifact data={data} title={artifact.title} />;
    case "skill_gap":
      return <SkillGapArtifact data={data} title={artifact.title} />;
    default:
      return null; // unknown types are ignored — never rendered as raw JSON
  }
}

/* --------------------------------- match --------------------------------- */

function MatchArtifact({ data, title }: { data?: unknown; title?: string }) {
  const match = normalizeMatch(pick(data, "match") ?? data);
  if (!match) return null;
  const evidence: Evidence[] = match.evidence ?? [];
  const dims =
    match.dimensions?.length
      ? match.dimensions
      : [
          { key: "technical", label: "Technical", score: match.technical },
          { key: "experience", label: "Experience", score: match.experience },
          { key: "projects", label: "Projects", score: match.projects },
          { key: "education", label: "Education", score: match.education },
        ].filter((d) => d.score != null);
  return (
    <Card className="border-primary/25">
      <CardContent className="flex flex-col gap-3">
        <div className="flex items-center gap-3">
          <MatchRing value={match.overall} size={56} thickness={5} label="Match" />
          <div className="min-w-0">
            <p className="text-2xs font-medium tracking-wide text-muted-foreground uppercase">
              {title ?? "Match analysis"}
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
              Open job
              <ArrowRight aria-hidden />
            </Link>
          </Button>
        )}
      </CardContent>
    </Card>
  );
}

/* -------------------------------- job_list -------------------------------- */

function JobListArtifact({ data, title }: { data?: unknown; title?: string }) {
  const page = normalizePage(data, normalizeJob);
  const jobs = page.items.length ? page.items : normalizePage(pick(data, "jobs") ?? data, normalizeJob).items;
  if (!jobs.length) return null;
  return (
    <Card className="border-primary/25">
      <CardContent className="space-y-2.5">
        <p className="flex items-center gap-1.5 text-2xs font-medium tracking-wide text-muted-foreground uppercase">
          <Briefcase className="size-3.5" aria-hidden />
          {title ?? `${jobs.length} matching roles`}
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

function TailorArtifact({ data, title }: { data?: unknown; title?: string }) {
  const t = normalizeTailor(data);
  const diff = t.diff;
  const text = t.tailored?.markdown ?? t.tailored?.text;
  if (!diff && !text) return null;
  return (
    <Card className="border-primary/25">
      <CardContent className="space-y-3">
        <p className="flex items-center gap-1.5 text-2xs font-medium tracking-wide text-muted-foreground uppercase">
          <Sparkles className="size-3.5" aria-hidden />
          {title ?? "Tailored resume draft"}
        </p>
        {diff && (diff.accepted.length > 0 || diff.rejected.length > 0) ? (
          <DiffView accepted={diff.accepted} rejected={diff.rejected} notes={t.notes} />
        ) : text ? (
          <StreamingText content={text} className="max-h-72 overflow-y-auto text-xs" />
        ) : null}
        {t.evidence && t.evidence.length > 0 && (
          <EvidenceList items={t.evidence} limit={2} dense />
        )}
        {text && <CopyButton text={text} label="Copy draft" />}
      </CardContent>
    </Card>
  );
}

/* ------------------------------- cover_letter ------------------------------ */

function CoverLetterArtifact({ data, title }: { data?: unknown; title?: string }) {
  const text = coverLetterText(data);
  if (!text) return null;
  return (
    <Card className="border-primary/25">
      <CardContent className="space-y-3">
        <p className="flex items-center gap-1.5 text-2xs font-medium tracking-wide text-muted-foreground uppercase">
          <FileText className="size-3.5" aria-hidden />
          {title ?? "Cover letter draft"}
        </p>
        <StreamingText content={text} className="max-h-80 overflow-y-auto" />
        <CopyButton text={text} label="Copy letter" />
      </CardContent>
    </Card>
  );
}

/* ----------------------------- interview_session ---------------------------- */

function InterviewArtifact({ data, title }: { data?: unknown; title?: string }) {
  const id = str(data, "sessionId", "session_id", "id") ?? str(pick(data, "session"), "id");
  if (!id) return null;
  return (
    <Card className="border-primary/25">
      <CardContent className="flex flex-wrap items-center gap-3">
        <span className="flex size-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
          <CalendarClock className="size-4.5" aria-hidden />
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium">{title ?? "Mock interview ready"}</p>
          <p className="text-xs text-muted-foreground">
            The agent prepared a session from this conversation.
          </p>
        </div>
        <Button variant="ai" size="sm" asChild>
          <Link href={`/interviews/${id}`}>
            Start
            <ArrowRight aria-hidden />
          </Link>
        </Button>
      </CardContent>
    </Card>
  );
}

/* --------------------------------- gaps ---------------------------------- */

function SkillGapArtifact({ data, title }: { data?: unknown; title?: string }) {
  const items = listOf(data, "gaps", "skillGaps", "skill_gaps", "items").map((g) => ({
    skill: str(g, "skill", "name") ?? String(g),
    importance: str(g, "importance", "priority"),
    reason: str(g, "reason", "why"),
  }));
  if (!items.length) return null;
  return (
    <Card className="border-primary/25">
      <CardContent className="space-y-2">
        <p className="flex items-center gap-1.5 text-2xs font-medium tracking-wide text-muted-foreground uppercase">
          <Layers className="size-3.5" aria-hidden />
          {title ?? "Skill gaps"}
        </p>
        <SkillChips missing={items.map((i) => i.skill)} max={12} />
        <ul className="space-y-1">
          {items.slice(0, 4).map((g, i) => (
            <li key={i} className="text-xs text-muted-foreground">
              <span className="font-medium text-foreground">{g.skill}</span>
              {g.reason ? ` — ${g.reason}` : ""}
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
