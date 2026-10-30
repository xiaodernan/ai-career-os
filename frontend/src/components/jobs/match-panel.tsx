"use client";

import * as React from "react";
import { AlertTriangle, Compass, Lightbulb, Sparkles, Target } from "lucide-react";
import { cn } from "@/lib/utils";
import { formatDateTime } from "@/lib/format";
import { useLocale } from "@/lib/i18n/locale-context";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { MatchRing, scoreBand } from "@/components/ai/match-ring";
import { DimensionBars, SkillChips } from "@/components/common/skill-chips";
import { SectionHeading } from "@/components/common/export-buttons";
import { AIBadge } from "@/components/ai/ai-badge";
import type { JobMatch, PreparationItem, SkillGap } from "@/lib/api/types";
import { matchDimensionLabel } from "@/lib/dimensions";
import { requirementPriorityWord } from "@/lib/status-words";

/**
 * Match breakdown (§10): every number here is traceable — the ring is the
 * aggregate, the bars are the per-dimension scores, and the evidence list
 * (rendered by the page) carries the quotes behind them.
 */

export function MatchPanel({
  match,
  analyzing,
  onAnalyze,
  className,
}: {
  match: JobMatch | null;
  analyzing?: boolean;
  onAnalyze?: () => void;
  className?: string;
}) {
  const { t, locale } = useLocale();
  // The dimension names come from the shared vocabulary, so the bar the
  // reader sees says the same thing the copilot's artifact says and the
  // interview report says -- in the reader's language.
  const fallbackDims: { key: string; label: string; score?: number }[] = match
    ? match.dimensions?.length
      ? match.dimensions
      : [
          { key: "technical", score: match.technical },
          { key: "experience", score: match.experience },
          { key: "projects", score: match.projects },
          { key: "education", score: match.education },
        ]
          .filter((d) => d.score != null)
          .map((d) => ({ ...d, label: matchDimensionLabel(t, d.key) }))
    : [];

  return (
    <Card className={className}>
      <CardHeader>
        <SectionHeading
          eyebrow={t("eyebrows.aiMatch")}
          icon={<Target className="size-4" aria-hidden />}
          title={match ? t("jobs.match.whyTitle") : t("jobs.match.noMatchYet")}
          description={
            match
              ? t("jobs.match.evidenceNote")
              : t("jobs.match.runToScore")
          }
          action={
            onAnalyze ? (
              <button
                type="button"
                onClick={onAnalyze}
                disabled={analyzing}
                className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-input bg-card px-3 text-sm font-medium shadow-[0_1px_0_0_var(--border)] transition-colors hover:bg-accent focus-visible:ring-[3px] focus-visible:ring-ring/35 disabled:opacity-55"
              >
                <Sparkles className={cn("size-4", analyzing && "animate-spin")} aria-hidden />
                {analyzing ? t("jobs.match.analyzing") : match ? t("jobs.match.rerun") : t("jobs.match.analyze")}
              </button>
            ) : null
          }
        />
      </CardHeader>
      <CardContent className="space-y-4">
        {!match ? (
          <div className="flex items-center gap-3 rounded-lg border border-dashed border-border bg-muted/30 p-4">
            <MatchRing value={0} size={56} thickness={5} animated={false} label={t("jobs.match.noMatch")} />
            <p className="text-sm text-muted-foreground">
              {t("jobs.match.nothingFabricatedBefore")}{" "}
              <span className="font-medium text-foreground">/jobs/&#123;id&#125;/match</span>{" "}
              {t("jobs.match.nothingFabricatedAfter")}
            </p>
          </div>
        ) : (
          <>
            <div className="flex flex-wrap items-center gap-4">
              <MatchRing value={match.overall} size={84} thickness={7} label={t("jobs.match.overall")} />
              <div className="min-w-0 flex-1 space-y-1">
                <p className="text-sm font-medium">
                  {match.overall >= 80
                    ? t("jobs.match.strong")
                    : match.overall >= 60
                      ? t("jobs.match.good")
                      : match.overall >= 40
                        ? t("jobs.match.partial")
                        : t("jobs.match.weak")}
                </p>
                <p className="text-xs text-muted-foreground">
                  {match.reasoning ??
                    t("jobs.match.evidenceLine", {
                      matched: match.matchedSkills?.length ?? 0,
                      missing: match.missingSkills?.length ?? 0,
                      plural: (match.missingSkills?.length ?? 0) === 1 ? "" : "s",
                    })}
                </p>
                {match.createdAt && (
                  <p className="text-2xs text-muted-foreground">
                    {t("jobs.match.computedAt", {
                      when: formatDateTime(match.createdAt, locale),
                    })}
                  </p>
                )}
              </div>
              <AIBadge label={t("jobs.match.evidenceBacked")} className="self-start" />
            </div>

            <DimensionBars dimensions={fallbackDims} />

            <SkillChips matched={match.matchedSkills} missing={match.missingSkills} max={14} showLabels />

            {match.whyMatch && match.whyMatch.length > 0 && (
              <ul className="space-y-1.5 border-t border-border/60 pt-3">
                {match.whyMatch.slice(0, 4).map((w, i) => (
                  <li key={i} className="flex gap-2 text-sm">
                    <span
                      className={cn(
                        "mt-1.5 size-1.5 shrink-0 rounded-full",
                        scoreBand(match.overall) === "strong" ? "bg-success" : "bg-primary"
                      )}
                      aria-hidden
                    />
                    <span className="text-muted-foreground">{w}</span>
                  </li>
                ))}
              </ul>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}

/* ------------------------------------------------------------------ */

export function SkillGapCard({ gaps, className }: { gaps: SkillGap[]; className?: string }) {
  const { t } = useLocale();
  if (!gaps.length) return null;
  return (
    <Card className={className}>
      <CardHeader>
        <SectionHeading
          eyebrow={t("eyebrows.growth")}
          icon={<AlertTriangle className="size-4" aria-hidden />}
          title={t("jobs.match.skillGaps")}
          description={t("jobs.match.skillGapsDescription")}
        />
      </CardHeader>
      <CardContent>
        <ul className="space-y-2.5">
          {gaps.map((g, i) => (
            <li key={`${g.skill}-${i}`} className="flex items-start gap-2.5">
              <span
                className={cn(
                  "mt-1 size-1.5 shrink-0 rounded-full",
                  g.importance === "critical" || g.importance === "must"
                    ? "bg-destructive"
                    : g.importance === "high"
                      ? "bg-warning"
                      : "bg-muted-foreground/50"
                )}
                aria-hidden
              />
              <div className="min-w-0 flex-1">
                <p className="flex flex-wrap items-center gap-2 text-sm font-medium">
                  {g.skill}
                  {g.importance && (
                    <Badge variant={g.importance === "critical" || g.importance === "must" ? "destructive" : "outline"} className="text-2xs font-normal">
                      {requirementPriorityWord(t, g.importance)}
                    </Badge>
                  )}
                </p>
                {g.reason && <p className="text-xs text-muted-foreground">{g.reason}</p>}
              </div>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}

export function InterviewTopicsCard({ topics, className }: { topics: string[]; className?: string }) {
  const { t } = useLocale();
  if (!topics.length) return null;
  return (
    <Card className={className}>
      <CardHeader>
        <SectionHeading
          eyebrow={t("eyebrows.prep")}
          icon={<Compass className="size-4" aria-hidden />}
          title={t("jobs.match.interviewTopics")}
          description={t("jobs.match.interviewTopicsDescription")}
        />
      </CardHeader>
      <CardContent>
        <ol className="space-y-2">
          {topics.map((t, i) => (
            <li key={`${t}-${i}`} className="flex items-center gap-2.5 text-sm">
              <span className="flex size-5 shrink-0 items-center justify-center rounded-md bg-muted font-mono text-2xs text-muted-foreground tabular-nums">
                {i + 1}
              </span>
              {t}
            </li>
          ))}
        </ol>
      </CardContent>
    </Card>
  );
}

export function PreparationCard({ items, className }: { items: PreparationItem[]; className?: string }) {
  const { t } = useLocale();
  const list = items.filter((i) => i?.topic || i?.title || i?.reason);
  if (!list.length) return null;
  return (
    <Card className={className}>
      <CardHeader>
        <SectionHeading
          eyebrow={t("eyebrows.prep")}
          icon={<Lightbulb className="size-4" aria-hidden />}
          title={t("jobs.match.preparation")}
          description={t("jobs.match.preparationDescription")}
        />
      </CardHeader>
      <CardContent>
        <ul className="space-y-3">
          {list.map((item, i) => (
            <li key={i} className="rounded-lg border border-border/70 bg-muted/20 p-3">
              <p className="flex flex-wrap items-center gap-2 text-sm font-medium">
                {item.title ?? item.topic}
                {item.priority && (
                  <Badge variant="outline" className="text-2xs font-normal capitalize">
                    {item.priority}
                  </Badge>
                )}
                {typeof item.hours === "number" && (
                  <Badge variant="secondary" className="text-2xs font-normal tabular-nums">
                    ~{item.hours}h
                  </Badge>
                )}
              </p>
              {item.reason && <p className="mt-1 text-xs text-muted-foreground">{item.reason}</p>}
              {item.resource && (
                <p className="mt-1 truncate text-xs text-muted-foreground">
                  <span className="font-medium text-foreground">
                    {t("jobs.match.resource")}{" "}
                  </span>
                  {item.resource}
                </p>
              )}
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}

/** Job description card — collapsible raw text so the detail page stays scannable. */
export function JdCard({
  rawText,
  requiredSkills,
  preferredSkills,
  responsibilities,
  className,
}: {
  rawText?: string | null;
  requiredSkills?: string[];
  preferredSkills?: string[];
  responsibilities?: string[];
  className?: string;
}) {
  const [open, setOpen] = React.useState(false);
  const { t } = useLocale();
  const hasStructured = Boolean(requiredSkills?.length || preferredSkills?.length || responsibilities?.length);
  if (!rawText && !hasStructured) return null;

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="text-base">{t("jobs.match.jobDescription")}</CardTitle>
        {hasStructured && (
          <CardDescription>{t("jobs.match.jobDescriptionDescription")}</CardDescription>
        )}
      </CardHeader>
      <CardContent className="space-y-4">
        {requiredSkills && requiredSkills.length > 0 && (
          <div>
            <p className="mb-1.5 text-xs font-semibold tracking-wide text-muted-foreground uppercase">
              {t("jobs.match.required")}
            </p>
            <SkillChips matched={requiredSkills} max={20} />
          </div>
        )}
        {preferredSkills && preferredSkills.length > 0 && (
          <div>
            <p className="mb-1.5 text-xs font-semibold tracking-wide text-muted-foreground uppercase">
              {t("jobs.match.niceToHave")}
            </p>
            <SkillChips missing={preferredSkills} max={20} />
          </div>
        )}
        {responsibilities && responsibilities.length > 0 && (
          <ul className="ml-4 list-disc space-y-1 text-sm text-muted-foreground marker:text-border">
            {responsibilities.slice(0, 8).map((r, i) => (
              <li key={i}>{r}</li>
            ))}
          </ul>
        )}
        {rawText && (
          <div>
            <button
              type="button"
              onClick={() => setOpen((v) => !v)}
              aria-expanded={open}
              className="rounded-md text-xs font-medium text-primary underline-offset-4 hover:underline focus-visible:ring-[3px] focus-visible:ring-primary/30"
            >
              {open ? t("jobs.match.hideOriginal") : t("jobs.match.showOriginal")}
            </button>
            {open && (
              <pre className="animate-fade-in mt-2 max-h-80 overflow-auto rounded-lg border border-border/70 bg-muted/40 p-3 font-sans text-xs leading-relaxed whitespace-pre-wrap text-muted-foreground">
                {rawText}
              </pre>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export { CardDescription, CardTitle };
