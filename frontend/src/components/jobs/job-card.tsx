"use client";

import * as React from "react";
import Link from "next/link";
import { ArrowUpRight, Briefcase, MapPin, Wallet } from "lucide-react";
import { cn } from "@/lib/utils";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { MatchRing } from "@/components/ai/match-ring";
import { SkillChips } from "@/components/common/skill-chips";
import { SaveToggle } from "@/components/jobs/save-toggle";
import { formatSalary, relativeTime, titleCase } from "@/lib/format";
import { useLocale } from "@/lib/i18n/locale-context";
import type { Job } from "@/lib/api/types";

/**
 * JobCard — deliberately not a job-board card: the AI match ring and the
 * why/missing evidence lead, the metadata follows (PRD §7).
 */
export interface JobCardProps extends React.ComponentProps<"div"> {
  job: Job;
  /** compact = dashboard/artifact lists, full = search results */
  dense?: boolean;
  showSave?: boolean;
  /** override the detail route (saved list, artifacts) */
  href?: string;
}

function JobCard({
  job,
  dense = false,
  showSave = true,
  href,
  className,
  ...props
}: JobCardProps) {
  const match = job.latestMatch ?? null;
  const { t } = useLocale();
  const to = href ?? `/jobs/${job.id}`;
  const salary = formatSalary(job.salaryMin, job.salaryMax, job.salaryCurrency);
  const company = job.company?.name || job.companyName;

  return (
    <Card
      className={cn(
        "group relative gap-2 overflow-hidden p-4 transition-shadow duration-200 hover:shadow-pop",
        className
      )}
      {...props}
    >
      <div className="flex items-start gap-3.5">
        {match ? (
          <MatchRing
            value={match.overall}
            size={dense ? 44 : 56}
            thickness={dense ? 4 : 5}
            label={t("jobCard.matchFor", { title: job.title })}
          />
        ) : (
          <span
            className={cn(
              "flex shrink-0 items-center justify-center rounded-full border border-dashed border-border text-muted-foreground",
              dense ? "size-11" : "size-14"
            )}
            title={t("jobCard.noMatchYet")}
            aria-label={t("jobCard.noMatchYet")}
          >
            <Briefcase className="size-4" aria-hidden />
          </span>
        )}

        <div className="min-w-0 flex-1">
          <div className="flex items-start gap-2">
            <div className="min-w-0 flex-1">
              <h3 className="truncate text-sm font-semibold leading-snug">
                <Link
                  href={to}
                  className="rounded-md outline-none after:absolute after:inset-0 focus-visible:ring-[3px] focus-visible:ring-primary/30 hover:text-primary"
                >
                  {job.title}
                </Link>
              </h3>
              <p className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-muted-foreground">
                <span className="truncate font-medium">{company || t("jobCard.companyNotResearched")}</span>
                {job.location && (
                  <span className="inline-flex items-center gap-1">
                    <span aria-hidden>·</span>
                    <MapPin className="size-3" aria-hidden />
                    {job.location}
                  </span>
                )}
                {salary && (
                  <span className="inline-flex items-center gap-1">
                    <span aria-hidden>·</span>
                    <Wallet className="size-3" aria-hidden />
                    {salary}
                  </span>
                )}
              </p>
            </div>
            {showSave && (
              <span className="relative z-10 -mr-1 -mt-1">
                <SaveToggle jobId={job.id} saved={job.saved} />
              </span>
            )}
          </div>

          {/* Boolean() is load-bearing: an `&&` on a length short-circuits to the number 0, and React
              renders that as the text "0" -- which is what every unscored dashboard row printed. */}
          {Boolean(match?.matchedSkills?.length || match?.missingSkills?.length || job.skills?.length) && (
            <div className="mt-2.5">
              {match ? (
                <SkillChips matched={match.matchedSkills} missing={match.missingSkills} max={dense ? 4 : 6} showLabels />
              ) : (
                <ul className="flex flex-wrap gap-1.5">
                  {(job.skills ?? []).slice(0, dense ? 3 : 6).map((s) => (
                    <li key={s}>
                      <Badge variant="outline" className="text-2xs font-normal">
                        {s}
                      </Badge>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}

          {!dense && match?.whyMatch?.length ? (
            <p className="mt-2 line-clamp-2 text-xs text-muted-foreground">
              <span className="font-medium text-foreground">
                {t("jobCard.whyThisJob")}{" "}
              </span>
              {match.whyMatch[0]}
            </p>
          ) : null}
        </div>
      </div>

      <div className="flex items-center justify-between gap-2 pt-0.5 text-2xs text-muted-foreground">
        <span className="flex items-center gap-2">
          {job.status && job.status !== "open" && (
            <Badge variant="secondary" className="text-2xs">
              {titleCase(job.status)}
            </Badge>
          )}
          {job.remoteType && <span className="capitalize">{titleCase(job.remoteType)}</span>}
          {job.source === "user_paste" && <span>{t("jobCard.pastedJd")}</span>}
          {job.source === "agent_research" && <span>{t("jobCard.foundByResearch")}</span>}
        </span>
        <span className="flex items-center gap-1">
          {job.postedAt && <span>{relativeTime(job.postedAt)}</span>}
          <ArrowUpRight className="size-3 opacity-0 transition-opacity duration-150 group-hover:opacity-100" aria-hidden />
        </span>
      </div>
    </Card>
  );
}

export { JobCard };
