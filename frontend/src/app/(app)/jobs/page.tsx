"use client";

import * as React from "react";
import Link from "next/link";
import { Bookmark, Briefcase, SlidersHorizontal, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";
import { PageHeader } from "@/components/common/page-header";
import { QueryBoundary } from "@/components/common/query-boundary";
import { LoadingJobCardSkeleton } from "@/components/common/loading-skeletons";
import { Pagination } from "@/components/common/pagination";
import { lastPageOf } from "@/lib/page-window";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { JobCard } from "@/components/jobs/job-card";
import { JobFilterPanel } from "@/components/jobs/job-filters";
import { AnalyzeJdDialog } from "@/components/jobs/analyze-jd-dialog";
import { ImportJobDialog } from "@/components/jobs/import-job-dialog";
import { relativeTime } from "@/lib/format";
import { useJobs, useResumes, useResume, useSavedJobs } from "@/lib/hooks/resources";
import { useUrlState } from "@/lib/hooks/use-url-state";
import { filterAndPaginate, hasActiveJobFilters, profileSkillSuggestions } from "@/lib/job-filter";

type FilterState = {
  q: string;
  skills: string;
  location: string;
  company: string;
  remote?: boolean;
  min_salary?: number;
  max_salary?: number;
  sort: string;
  page: number;
  size: number;
};

const DEFAULTS: FilterState = {
  q: "",
  skills: "",
  location: "",
  company: "",
  sort: "",
  page: 0,
  size: 12,
};

/**
 * The board's orderings. `auto` is the one spelled by *omission*: with no `sort`
 * parameter the server ranks a query by relevance and a browse by recency, which is
 * what a person means by "best match". The rest are `JobSearchRepository.ORDERINGS`
 *' own keys — a gate in job-filter.test.ts keeps the two lists identical, so an
 * ordering the SQL gains appears here rather than staying a curl-only feature.
 */
const SORT_OPTIONS: { value: string; label: string }[] = [
  { value: "auto", label: "Best match" },
  { value: "posted", label: "Newest first" },
  { value: "salary", label: "Highest salary" },
  { value: "title", label: "Title A–Z" },
  { value: "match", label: "Match score" },
];

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
    () => profileSkillSuggestions(resume.data?.structured),
    [resume.data?.structured]
  );

  const active = tab === "discover" ? jobs : saved;
  // `GET /jobs/saved` accepts no query parameters and returns the whole bookmark set,
  // so on this tab the panel's predicates run here over rows already in hand —
  // otherwise every control still moves the URL while the wire carries nothing.
  // Discover keeps filtering in SQL; both tabs read the same filter values.
  const savedPage = React.useMemo(
    () => (saved.data ? filterAndPaginate(saved.data.items, filters) : undefined),
    [saved.data, filters]
  );
  // Only `data` is swapped, and react-query's result is a discriminated union the
  // spread cannot re-narrow on its own, so the swap is asserted back into shape.
  const listView = tab === "saved" ? ({ ...saved, data: savedPage } as typeof saved) : jobs;
  const total = listView.data?.total ?? 0;
  // Empty means two different things on the Saved tab and only one of them is "you
  // have saved nothing": a filter can empty a list that still has rows behind it.
  const savedFilteredToEmpty =
    tab === "saved" && hasActiveJobFilters(filters) && (saved.data?.items.length ?? 0) > 0;
  // The same correction as the applications board, over the window both tabs share: the
  // answer's own window is the divisor (`data.size`) and `lastPageOf`
  // (lib/page-window.ts) is that rule in one place, so a past-the-end page lands on the
  // last page that exists. On Saved the window is the client's and `filterAndPaginate`
  // already clamps, so the write there only names the page the clamp already chose. A
  // layout effect, because the stale commit paints its empty copy first -- React flushes
  // this update before the browser paints, so the wrong screen is replaced, not seen.
  const lastPage = listView.data ? lastPageOf(total, listView.data.size) : 0;
  React.useLayoutEffect(() => {
    if (listView.data && filters.page > lastPage) setFilters({ page: lastPage });
  }, [listView.data, filters.page, lastPage, setFilters]);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Jobs"
        description="Discovered and pasted roles, scored against your resume with evidence — the match ring leads, the metadata follows."
        actions={
          <>
            <ImportJobDialog />
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
              resultCount={listView.data ? total : undefined}
              loading={active.isFetching}
            />
          </div>
        </aside>

        <div className="min-w-0 space-y-4">
          <div className="flex items-center justify-between gap-3">
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

            {/* Ordering is a Discover question: the Saved tab pages the bookmark set it
                already has, so a sort there would move the URL and nothing else. */}
            {tab === "discover" && (
              <div className="flex items-center gap-2">
                <Label htmlFor="jobs-sort" className="text-xs text-muted-foreground">
                  Sort
                </Label>
                <Select
                  value={filters.sort || "auto"}
                  onValueChange={(v) => setFilters({ sort: v === "auto" ? "" : v, page: 0 })}
                >
                  <SelectTrigger id="jobs-sort" size="sm" className="w-40">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {SORT_OPTIONS.map((option) => (
                      <SelectItem key={option.value} value={option.value}>
                        {option.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}
          </div>

          <QueryBoundary
            query={listView}
            skeleton={<LoadingJobCardSkeleton count={4} />}
            className="gap-3"
            empty={
              tab === "saved" && savedFilteredToEmpty
                ? {
                    icon: <SlidersHorizontal aria-hidden />,
                    title: "No saved role matches these filters",
                    description:
                      "You have bookmarks behind this filter set. Loosen one, or clear them all to see the whole saved list.",
                    action: (
                      <Button variant="outline" size="sm" onClick={() => setFilters(DEFAULTS, { replaceAll: true })}>
                        Clear filters
                      </Button>
                    ),
                  }
                : tab === "saved"
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
              title:
                tab === "saved"
                  ? "This API build has no saved-jobs list"
                  : "This API build has no job search",
              description:
                "The route answered 404, so this frontend and the backend it is talking to are different versions. Nothing is shown in place of the real rows.",
            }}
          >
            {(page) => (
              <>
                <ul className="flex flex-col gap-3">
                  {page.items.map((job) => (
                    <li key={job.id}>
                      <JobCard job={tab === "saved" ? { ...job, saved: true } : job} />
                      {tab === "saved" && (job.note || job.savedAt) ? (
                        <div className="mt-1.5 space-y-0.5 px-1 text-xs text-muted-foreground">
                          {job.savedAt ? <p>Saved {relativeTime(job.savedAt)}</p> : null}
                          {job.note ? (
                            <p>
                              <span className="font-medium text-foreground">Note: </span>
                              {job.note}
                            </p>
                          ) : null}
                        </div>
                      ) : null}
                    </li>
                  ))}
                </ul>
                {total > filters.size && (
                  <Pagination
                    page={listView.data?.page ?? filters.page}
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
