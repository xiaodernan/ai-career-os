"use client";

import * as React from "react";
import Link from "next/link";
import { ArrowRight, Briefcase, CalendarClock, FileText, Sparkles } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { MatchRing } from "@/components/ai/match-ring";
import { SkillChips, DimensionBars } from "@/components/common/skill-chips";
import { DiffView } from "@/components/common/diff-view";
import { EvidenceList } from "@/components/ai/evidence-list";
import dynamic from "next/dynamic";
import { CopyButton } from "@/components/common/export-buttons";
import { JobCard } from "@/components/jobs/job-card";
import {
  normalizeJob,
  normalizeMatch,
  normalizePage,
  normalizeTailor,
  pick,
  str,
  coverLetterText,
} from "@/lib/api/normalize";
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
    default:
      return null; // unknown types are ignored — never rendered as raw JSON
  }
}

/* --------------------------------- match --------------------------------- */

function MatchArtifact({ data }: { data?: unknown }) {
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
              Match analysis
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

function JobListArtifact({ data }: { data?: unknown }) {
  const page = normalizePage(data, normalizeJob);
  const jobs = page.items.length ? page.items : normalizePage(pick(data, "jobs") ?? data, normalizeJob).items;
  if (!jobs.length) return null;
  return (
    <Card className="border-primary/25">
      <CardContent className="space-y-2.5">
        <p className="flex items-center gap-1.5 text-2xs font-medium tracking-wide text-muted-foreground uppercase">
          <Briefcase className="size-3.5" aria-hidden />
          {jobs.length} matching roles
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
  const t = normalizeTailor(data);
  const diff = t.diff;
  const text = t.tailored?.markdown;
  if (!diff && !text) return null;
  return (
    <Card className="border-primary/25">
      <CardContent className="space-y-3">
        <p className="flex items-center gap-1.5 text-2xs font-medium tracking-wide text-muted-foreground uppercase">
          <Sparkles className="size-3.5" aria-hidden />
          Tailored resume draft
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

function CoverLetterArtifact({ data }: { data?: unknown }) {
  const text = coverLetterText(data);
  if (!text) return null;
  return (
    <Card className="border-primary/25">
      <CardContent className="space-y-3">
        <p className="flex items-center gap-1.5 text-2xs font-medium tracking-wide text-muted-foreground uppercase">
          <FileText className="size-3.5" aria-hidden />
          Cover letter draft
        </p>
        <StreamingText content={text} className="max-h-80 overflow-y-auto" />
        <CopyButton text={text} label="Copy letter" />
      </CardContent>
    </Card>
  );
}

/* ----------------------------- interview_session ---------------------------- */

function InterviewArtifact({ data }: { data?: unknown }) {
  const id = str(data, "sessionId", "session_id", "id") ?? str(pick(data, "session"), "id");
  if (!id) return null;
  return (
    <Card className="border-primary/25">
      <CardContent className="flex flex-wrap items-center gap-3">
        <span className="flex size-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
          <CalendarClock className="size-4.5" aria-hidden />
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium">Mock interview ready</p>
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

/* `skill_gap` was a case here, with this renderer under it, until #145a measured that no path through
 * `_collect_artifacts` ever appends that type: the card could not be reached, while the job page's own
 * gap panel -- fed by the persisted `skillGaps` column, which #126 gave a real producer -- is where
 * gaps actually show. The gate that compares this switch with the types the orchestrator writes is
 * what would catch its return. */

