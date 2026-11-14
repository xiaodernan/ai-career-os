"use client";

import * as React from "react";
import Link from "next/link";
import dynamic from "next/dynamic";
import { Bookmark, Briefcase, SlidersHorizontal, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";
import { PageHeader } from "@/components/common/page-header";
import { GradientText } from "@/components/ui/gradient-text";
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
import { SavedSearchPanel } from "@/components/jobs/saved-search-panel";
// The two AI dialogs are the heaviest things the jobs board ships; they are
// below the fold and open on click, so they leave the first-load path (the
// bundle budget holds the line at 310 kB gzip).
const AnalyzeJdDialog = dynamic(() =>
  import("@/components/jobs/analyze-jd-dialog").then((m) => m.AnalyzeJdDialog),
);
const ImportJobDialog = dynamic(() =>
  import("@/components/jobs/import-job-dialog").then((m) => m.ImportJobDialog),
);
import { relativeTime } from "@/lib/format";
import { useJobs, useResumes, useResume, useSavedJobs } from "@/lib/hooks/resources";
import { useUrlState } from "@/lib/hooks/use-url-state";
import { useLocale } from "@/lib/i18n/locale-context";
import { hasActiveJobFilters, profileSkillSuggestions } from "@/lib/job-filter";

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
const SORT_OPTIONS: { value: string; labelKey: string }[] = [
  { value: "auto", labelKey: "jobs.sort.auto" },
  { value: "posted", labelKey: "jobs.sort.posted" },
  { value: "salary", labelKey: "jobs.sort.salary" },
  { value: "title", labelKey: "jobs.sort.title" },
  { value: "match", labelKey: "jobs.sort.match" },
];

export default function JobsPage() {
  const { t, locale } = useLocale();
  const [filters, setFilters] = useUrlState(DEFAULTS, {
    numericKeys: ["page", "min_salary", "max_salary", "size"],
    booleanKeys: ["remote"],
  });
  const [tab, setTab] = React.useState<"discover" | "saved">("discover");
  const [mobileFilters, setMobileFilters] = React.useState(false);

  const jobs = useJobs(tab === "discover" ? filters : { size: filters.size, page: filters.page });
  // Both tabs send the panel and the window. The shelf answers both in SQL now (74.1/74.2), so
  // the bookmarks that come back are the ones the reader asked about, in one clamped page, with a
  // count the server made -- and this screen no longer decides which rows match nor how the page is
  // cut.
  const saved = useSavedJobs(tab === "saved" ? filters : undefined);
  const resumes = useResumes();
  const firstResumeId = resumes.data?.items?.[0]?.id ?? null;
  const resume = useResume(firstResumeId);
  const suggestions = React.useMemo(
    () => profileSkillSuggestions(resume.data?.structured),
    [resume.data?.structured]
  );

  const listView = tab === "discover" ? jobs : saved;
  const total = listView.data?.total ?? 0;
  // Both tabs now ask the server the same question, and a filtered answer says nothing about how
  // many rows sit behind the filter. What either tab can say is whether a filter is set -- and with
  // none set the copy must not blame them for the emptiness.
  const filteredToEmpty = hasActiveJobFilters(filters);
  // The same correction as the applications board, over the window both tabs share: the
  // answer's own window is the divisor (`data.size`) and `lastPageOf`
  // (lib/page-window.ts) is that rule in one place, so a past-the-end page lands on the
  // last page that exists. Both windows are the server's (74.1 predicates, 74.2 window),
  // and the total is the server's own COUNT, so the clamp only names the page the server
  // would clamp to anyway. A layout effect, because the stale commit paints its empty copy
  // first -- React flushes this update before the browser paints, so the wrong screen is
  // replaced, not seen.
  const lastPage = listView.data ? lastPageOf(total, listView.data.size) : 0;
  React.useLayoutEffect(() => {
    if (listView.data && filters.page > lastPage) setFilters({ page: lastPage });
  }, [listView.data, filters.page, lastPage, setFilters]);

  return (
    <div className="space-y-6">
      {/* The job board is the highest-frequency signed-in surface after the dashboard and inbox,
          and the one whose actions already lead into the AI copilot. It carries the same
          front-door band those two established: static light-theme washes, a dark-only aurora
          (screen-blend over a light Card would wash it white), a shimmer hairline and CSS-only
          staggered entrance. The blobs are plain decorated spans, so the band adds zero client
          JS and leaves the route budget untouched; every motion layer is decorative and
          `prefers-reduced-motion` stays authoritative via globals.css. */}
      <section className="animate-fade-up relative overflow-hidden rounded-2xl border hairline bg-card/60 shadow-card">
        {/* Light-theme ambient washes: static gradients, zero per-frame cost. */}
        <div
          aria-hidden
          className="pointer-events-none absolute -right-20 -top-24 h-64 w-64 rounded-full"
          style={{
            background:
              "radial-gradient(closest-side, color-mix(in oklch, var(--primary) 16%, transparent), transparent)",
          }}
        />
        <div
          aria-hidden
          className="pointer-events-none absolute -bottom-28 -left-24 h-64 w-64 rounded-full"
          style={{
            background:
              "radial-gradient(closest-side, color-mix(in oklch, var(--primary) 9%, transparent), transparent)",
          }}
        />
        {/* Dark-theme aurora: screen-blend light only ever composited over a dark surface. */}
        <div aria-hidden className="pointer-events-none absolute inset-0 hidden overflow-hidden dark:block">
          <span className="aurora-blob aurora-blob-1 opacity-30" />
          <span className="aurora-blob aurora-blob-2 opacity-30" />
          <div className="aurora-grid opacity-30" />
        </div>
        {/* Shimmer hairline crowns the band -- the same premium separator the dashboard uses. */}
        <span aria-hidden className="shimmer-rule absolute inset-x-0 top-0 block h-px" />
        <div className="relative px-6 py-6">
          <PageHeader
            title={<GradientText className="italic">{t("jobs.title")}</GradientText>}
            description={
              <span className="animate-fade-up block" style={{ animationDelay: "90ms" }}>
                {t("jobs.description")}
              </span>
            }
            actions={
              <div className="animate-fade-up flex flex-wrap items-center gap-2" style={{ animationDelay: "160ms" }}>
                <ImportJobDialog />
                <AnalyzeJdDialog />
                <Button variant="ai" size="sm" className="glow-halo glow-on-hover" asChild>
                  <Link href="/copilot">
                    <Sparkles aria-hidden />
                    {t("jobs.researchRoles")}
                  </Link>
                </Button>
              </div>
            }
          />
        </div>
      </section>

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
            {t("jobs.filtersButton")}
          </Button>
          <div className={cn("mt-3 rounded-xl border border-border/70 bg-card p-4 lg:mt-0 lg:border-0 lg:bg-transparent lg:p-0", !mobileFilters && "hidden lg:block")}>
            <SavedSearchPanel
              value={filters}
              onApply={(next) => setFilters(next, { replaceAll: true })}
            />
            <JobFilterPanel
              value={filters}
              onApply={(next) => setFilters(next, { replaceAll: true })}
              skillSuggestions={suggestions}
              resultCount={listView.data ? total : undefined}
              loading={listView.isFetching}
            />
          </div>
        </aside>

        <div className="min-w-0 space-y-4">
          <div className="flex items-center justify-between gap-3">
            <Tabs value={tab} onValueChange={(v) => { setTab(v as typeof tab); setFilters({ page: 0 }); }}>
              <TabsList variant="line">
                <TabsTrigger value="discover">
                  <Briefcase aria-hidden />
                  {t("jobs.discoverTab")}
                </TabsTrigger>
                <TabsTrigger value="saved">
                  <Bookmark aria-hidden />
                  {t("jobs.savedTab")}
                  {/* The shelf is filtered on the wire now (74.1), so this is the number of
                      bookmarks that answer the panel -- the same count the panel prints -- rather
                      than the size of the whole shelf. */}
                  {saved.data?.total ? (
                    <span className="ml-1 text-2xs text-muted-foreground tabular-nums">{saved.data.total}</span>
                  ) : null}
                </TabsTrigger>
              </TabsList>
            </Tabs>

            {/* Ordering is a Discover question: the shelf answers the panel's predicates but no
                sort, so a sort here would move the URL and nothing else -- 74.2 is where the Saved
                tab gets an ordering of its own, along with the window it needs one for. */}
            {tab === "discover" && (
              <div className="flex items-center gap-2">
                <Label htmlFor="jobs-sort" className="text-xs text-muted-foreground">
                  {t("jobs.sortLabel")}
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
                        {t(option.labelKey)}
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
              tab === "saved" && filteredToEmpty
                ? {
                    icon: <SlidersHorizontal aria-hidden />,
                    title: t("jobs.noSavedMatch"),
                    description: t("jobs.noSavedMatchDescription"),
                    action: (
                      <Button variant="outline" size="sm" onClick={() => setFilters(DEFAULTS, { replaceAll: true })}>
                        {t("jobs.clearFilters")}
                      </Button>
                    ),
                  }
                : tab === "saved"
                  ? {
                      icon: <Bookmark aria-hidden />,
                      title: t("jobs.nothingSaved"),
                      description: t("jobs.nothingSavedDescription"),
                      action: (
                        <Button variant="outline" size="sm" onClick={() => setTab("discover")}>
                          {t("jobs.browseDiscover")}
                        </Button>
                      ),
                    }
                  : filteredToEmpty
                    ? {
                        icon: <Briefcase aria-hidden />,
                        title: t("jobs.boardIsQuiet"),
                        description: t("jobs.boardIsQuietDescription"),
                        action: (
                          <>
                            <Button variant="outline" size="sm" onClick={() => setFilters(DEFAULTS, { replaceAll: true })}>
                              {t("jobs.clearFilters")}
                            </Button>
                            <Button variant="ai" size="sm" asChild>
                              <Link href="/copilot">{t("jobs.askCopilot")}</Link>
                            </Button>
                          </>
                        ),
                      }
                    : {
                        icon: <Briefcase aria-hidden />,
                        promise: t("jobs.boardEmptyPromise"),
                        proofs: [
                          t("jobs.boardEmptyProof1"),
                          t("jobs.boardEmptyProof2"),
                          t("jobs.boardEmptyProof3"),
                        ],
                        title: t("jobs.boardEmpty"),
                        description: t("jobs.boardEmptyDescription"),
                        action: (
                          <Button variant="ai" size="sm" asChild>
                            <Link href="/copilot">{t("jobs.askCopilot")}</Link>
                          </Button>
                        ),
                      }
            }
            notLive={{
              title:
                tab === "saved"
                  ? t("jobs.notLiveSavedTitle")
                  : t("jobs.notLiveSearchTitle"),
              description:
                t("jobs.notLiveDescription"),
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
                          {job.savedAt ? <p>{t("jobs.savedAt", { date: relativeTime(job.savedAt, locale) })}</p> : null}
                          {job.note ? (
                            <p>
                              <span className="font-medium text-foreground">
                                {t("jobs.noteLabel")}
                              </span>
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
                    label={t("jobs.paginationLabel")}
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
