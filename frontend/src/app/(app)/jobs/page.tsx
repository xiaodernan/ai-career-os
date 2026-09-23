"use client";

import * as React from "react";
import Link from "next/link";
import { Bookmark, Briefcase, SlidersHorizontal, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";
import { PageHeader } from "@/components/common/page-header";
import { QueryBoundary } from "@/components/common/query-boundary";
import { LoadingJobCardSkeleton } from "@/components/common/loading-skeletons";
import { Pagination } from "@/components/common/pagination";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { JobCard } from "@/components/jobs/job-card";
import { JobFilterPanel } from "@/components/jobs/job-filters";
import { AnalyzeJdDialog } from "@/components/jobs/analyze-jd-dialog";
import { useJobs, useResumes, useResume, useSavedJobs } from "@/lib/hooks/resources";
import { useUrlState } from "@/lib/hooks/use-url-state";
import { normalizeStructuredResume } from "@/lib/api/normalize";
import type { StructuredResume } from "@/lib/api/types";

type FilterState = {
  q: string;
  skills: string;
  location: string;
  company: string;
  remote?: boolean;
  min_salary?: number;
  max_salary?: number;
  page: number;
  size: number;
};

const DEFAULTS: FilterState = {
  q: "",
  skills: "",
  location: "",
  company: "",
  page: 0,
  size: 12,
};

function skillsFrom(structured?: StructuredResume | null): string[] {
  const s = normalizeStructuredResume(structured);
  if (!s) return [];
  const grouped = (s.skills ?? []).flatMap((g) => g.skills ?? []);
  return [...new Set([...grouped, ...(s.technologies ?? [])])].filter(Boolean).slice(0, 24);
}

export default function JobsPage() {
  const [filters, setFilters] = useUrlState(DEFAULTS, {
    numericKeys: ["page", "min_salary", "max_salary", "size"],
    booleanKeys: ["remote"],
  });
  const [tab, setTab] = React.useState<"discover" | "saved">("discover");
  const [mobileFilters, setMobileFilters] = React.useState(false);

  const jobs = useJobs(tab === "discover" ? filters : { size: filters.size, page: filters.page });
  const saved = useSavedJobs();
  const resumes = useResumes();
  const firstResumeId = resumes.data?.items?.[0]?.id ?? null;
  const resume = useResume(firstResumeId);
  const suggestions = React.useMemo(
    () => skillsFrom(resume.data?.structured),
    [resume.data?.structured]
  );

  const active = tab === "discover" ? jobs : saved;
  const total = active.data?.total ?? 0;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Jobs"
        description="Discovered and pasted roles, scored against your resume with evidence — the match ring leads, the metadata follows."
        actions={
          <>
            <AnalyzeJdDialog />
            <Button variant="ai" size="sm" asChild>
              <Link href="/copilot">
                <Sparkles aria-hidden />
                Research roles
              </Link>
            </Button>
          </>
        }
      />

      <div className="grid gap-6 lg:grid-cols-[15rem_minmax(0,1fr)]">
        <aside className="lg:sticky lg:top-20 lg:self-start">
          {/* Filters are always visible from lg up; collapsible on small screens */}
          <Button
            variant="outline"
            size="sm"
            className="w-full lg:hidden"
            aria-expanded={mobileFilters}
            onClick={() => setMobileFilters((v) => !v)}
          >
            <SlidersHorizontal aria-hidden />
            Filters
          </Button>
          <div className={cn("mt-3 rounded-xl border border-border/70 bg-card p-4 lg:mt-0 lg:border-0 lg:bg-transparent lg:p-0", !mobileFilters && "hidden lg:block")}>
            <JobFilterPanel
              value={filters}
              onApply={(next) => setFilters(next, { replaceAll: true })}
              skillSuggestions={suggestions}
              resultCount={active.data?.items.length ? total : undefined}
              loading={active.isFetching}
            />
          </div>
        </aside>

        <div className="min-w-0 space-y-4">
          <Tabs value={tab} onValueChange={(v) => { setTab(v as typeof tab); setFilters({ page: 0 }); }}>
            <TabsList variant="line">
              <TabsTrigger value="discover">
                <Briefcase aria-hidden />
                Discover
              </TabsTrigger>
              <TabsTrigger value="saved">
                <Bookmark aria-hidden />
                Saved
                {saved.data?.total ? (
                  <span className="ml-1 text-2xs text-muted-foreground tabular-nums">{saved.data.total}</span>
                ) : null}
              </TabsTrigger>
            </TabsList>
          </Tabs>

          <QueryBoundary
            query={active}
            skeleton={<LoadingJobCardSkeleton count={4} />}
            className="gap-3"
            empty={
              tab === "saved"
                ? {
                    icon: <Bookmark aria-hidden />,
                    title: "Nothing saved yet",
                    description:
                      "Save a role from Discover and it appears in your pipeline, ready for a match run and a tailored resume.",
                    action: (
                      <Button variant="outline" size="sm" onClick={() => setTab("discover")}>
                        Browse discover
                      </Button>
                    ),
                  }
                : {
                    icon: <Briefcase aria-hidden />,
                    title: "The job board is quiet",
                    description:
                      "No roles match these filters yet. Clear a filter, paste a JD for the analyst, or let Copilot research roles for your target.",
                    action: (
                      <>
                        <Button variant="outline" size="sm" onClick={() => setFilters(DEFAULTS, { replaceAll: true })}>
                          Clear filters
                        </Button>
                        <Button variant="ai" size="sm" asChild>
                          <Link href="/copilot">Ask Copilot</Link>
                        </Button>
                      </>
                    ),
                  }
            }
            notLive={{
              title: tab === "saved" ? "Saved jobs aren't connected yet" : "Job search isn't connected yet",
            }}
          >
            {(page) => (
              <>
                <ul className="flex flex-col gap-3">
                  {page.items.map((job) => (
                    <li key={job.id}>
                      <JobCard job={tab === "saved" ? { ...job, saved: true } : job} />
                    </li>
                  ))}
                </ul>
                {total > filters.size && (
                  <Pagination
                    page={filters.page}
                    size={filters.size}
                    total={total}
                    label="jobs"
                    onPageChange={(page) => {
                      setFilters({ page });
                      window.scrollTo({ top: 0, behavior: "smooth" });
                    }}
                  />
                )}
              </>
            )}
          </QueryBoundary>
        </div>
      </div>
    </div>
  );
}
