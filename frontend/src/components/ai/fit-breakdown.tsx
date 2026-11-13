"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { MatchRing } from "./match-ring";
import { SkillChips } from "@/components/common/skill-chips";
import { EvidenceCard } from "./evidence-card";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useLocale } from "@/lib/i18n/locale-context";
import { requirementPriorityWord } from "@/lib/status-words";
import type { Evidence, JobMatch } from "@/lib/api/types";

function DimensionBar({ label, value }: { label: string; value: number }) {
  const pct = Math.max(0, Math.min(100, value));
  return (
    <div className="space-y-1.5">
      <div className="flex items-baseline justify-between text-xs">
        <span className="capitalize text-muted-foreground">{label}</span>
        <span className="tabular-nums font-medium">{Math.round(pct)}%</span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
        <div
          className="h-full rounded-full bg-gradient-to-r from-primary/70 to-primary transition-[width] duration-700 ease-out"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

/**
 * FitBreakdown — the whole match result in one scannable column: the overall
 * ring, the four scored dimensions, the matched/missing skill split, the
 * model's own reasoning, the evidence behind it, the gaps worth closing and
 * the topics the interview will likely probe. Every claim above is either a
 * number or a quote the EvidenceCard can trace.
 */
export function FitBreakdown({ match, className }: { match: JobMatch; className?: string }) {
  const { t } = useLocale();
  const rawDims = [
    { key: "technical", label: t("studio.technical"), value: match.technical },
    { key: "experience", label: t("studio.experience"), value: match.experience },
    { key: "projects", label: t("studio.projects"), value: match.projects },
    { key: "education", label: t("studio.education"), value: match.education },
  ];
  const dims = rawDims
    .filter((d) => d.value != null)
    .map((d) => ({ label: d.label, value: d.value ?? 0 }));

  const hasSkills = (match.matchedSkills?.length ?? 0) + (match.missingSkills?.length ?? 0) > 0;
  const fitBand = match.overall >= 80 ? "strongFit"
    : match.overall >= 60 ? "goodFit"
    : match.overall >= 40 ? "partialFit"
    : "weakFit";

  return (
    <div className={cn("animate-fade-up space-y-4", className)}>
      <Card className="overflow-hidden">
        <CardHeader className="flex-row items-center gap-4 space-y-0">
          <MatchRing value={match.overall} size={88} />
          <div className="min-w-0">
            <CardTitle className="text-lg">{t("studio.fitReport")}</CardTitle>
            <p className="mt-0.5 text-sm text-muted-foreground">
              {t(`studio.${fitBand}`)}
              {match.reasoning ? ` — ${match.reasoning}` : ""}
            </p>
          </div>
        </CardHeader>
        {dims.length > 0 && (
          <CardContent className="grid gap-3 sm:grid-cols-2">
            {dims.map((d) => (
              <DimensionBar key={d.label} label={d.label} value={d.value} />
            ))}
          </CardContent>
        )}
      </Card>

      {hasSkills && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">{t("studio.skillsTitle")}</CardTitle>
          </CardHeader>
          <CardContent>
            <SkillChips
              matched={match.matchedSkills}
              missing={match.missingSkills}
              showLabels
              max={14}
            />
          </CardContent>
        </Card>
      )}

      {match.whyMatch?.length ? (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">{t("studio.whyMatchTitle")}</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="list-disc space-y-1 pl-5 text-sm text-muted-foreground marker:text-primary/60">
              {match.whyMatch.map((w, i) => (
                <li key={i}>{w}</li>
              ))}
            </ul>
          </CardContent>
        </Card>
      ) : null}

      {match.evidence?.length ? (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">{t("studio.evidenceTitle")}</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-2.5">
            {match.evidence.map((e: Evidence, i) => (
              <EvidenceCard
                key={i}
                quote={e.quote}
                docTitle={e.source?.docTitle}
                sourcePath={e.source?.path}
              />
            ))}
          </CardContent>
        </Card>
      ) : null}

      {match.skillGaps?.length ? (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">{t("studio.skillGapsTitle")}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {match.skillGaps.map((g, i) => (
              <div
                key={i}
                className="rounded-lg border border-border/70 bg-muted/30 p-3 text-sm"
              >
                <div className="flex items-center gap-2">
                  <span className="font-medium">{g.skill}</span>
                  {g.importance ? (
                    <Badge variant="outline" className="text-2xs">
                      {requirementPriorityWord(t, g.importance)}
                    </Badge>
                  ) : null}
                </div>
                {g.reason ? <p className="mt-1 text-muted-foreground">{g.reason}</p> : null}
              </div>
            ))}
          </CardContent>
        </Card>
      ) : null}

      {match.interviewTopics?.length ? (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">{t("studio.interviewTopicsTitle")}</CardTitle>
          </CardHeader>
          <CardContent>
            <SkillChips matched={match.interviewTopics} showLabels max={12} />
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
