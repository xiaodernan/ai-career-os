"use client";

import { notFound, useParams } from "next/navigation";
import Link from "next/link";
import { Building2, Globe, Tag, Code, Users, MapPin, ExternalLink } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/common/error-state";
import { useCompany } from "@/lib/hooks/resources";
import { useCompanyBrief } from "@/lib/hooks/growth";
import { formatSalary } from "@/lib/format";
import { ApiError } from "@/lib/api/client";
import type { CompanySource, Job } from "@/lib/api/types";

/**
 * One company's researched profile.
 *
 * Everything here is read under the name `CompanyItem` / `CompanyDetail` spells: the culture and
 * interview-process paragraphs are the `companies` row's own text columns (write-only until this page
 * existed), the sources are the jsonb column the schema requires external facts to carry, and the
 * roles are the board's own rows — each with the caller's latest cached match — capped at the
 * backend's paging ceiling. When the company has more open roles than the cap, the heading still
 * says the real total, so a short list never reads as the whole picture.
 */
export default function CompanyDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params?.id ?? null;
  const company = useCompany(id);
  // 4.8 — what the corpus says about this company. The engine reads the seeded
  // postings, so this is a deterministic read, not a generated summary. The hook
  // is called before the early returns below, because a hook after an early
  // return is a hook that is sometimes not called at all.
  const brief = useCompanyBrief();

  if (company.isPending) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-1/4" />
        <Skeleton className="h-4 w-1/2" />
        <Skeleton className="h-20 rounded-xl" />
        <Skeleton className="h-8 w-1/2" />
        <Skeleton className="h-8 w-1/4" />
        <span className="sr-only" role="status">
          Loading company…
        </span>
      </div>
    );
  }

  // Only a 404 is "this company isn't in the system". A 500 or a dropped connection is a
  // failure with a retry, not a missing record -- rendering it as a 404 tells the user to
  // go look for a company that does exist. (The local is named so it does not shadow the
  // `notFound()` route component from next/navigation.)
  const absent = company.error instanceof ApiError && company.error.isNotFound;
  if (absent) {
    notFound();
  }

  if (company.isError || !company.data) {
    return (
      <div className="space-y-6">
        <Card>
          <CardContent>
            <ErrorState
              title="Couldn't load this company"
              error={company.error}
              onRetry={() => void company.refetch()}
              retrying={company.isFetching}
            />
          </CardContent>
        </Card>
      </div>
    );
  }

  const c = company.data.company;
  const openRoles = company.data.openRoles;
  const total = c.openRoleCount ?? openRoles.length;

  return (
    <div className="space-y-6">
      <Card className="col-span-full">
        <CardHeader className="flex flex-row items-start gap-4 pb-3">
          <div className="flex size-20 shrink-0 items-center justify-center rounded-xl bg-muted">
            {c.logoUrl ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={c.logoUrl} alt={c.name} className="h-full w-full object-contain p-2" />
            ) : (
              <Building2 className="size-10 text-muted-foreground" aria-hidden />
            )}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-baseline gap-3 flex-wrap">
              <CardTitle className="text-2xl">{c.name}</CardTitle>
              {c.website && (
                <a
                  href={c.website}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-muted-foreground hover:text-foreground flex items-center gap-1"
                  aria-label={`${c.name} website`}
                >
                  <Globe className="size-3.5" aria-hidden />
                  Website
                </a>
              )}
            </div>
            <div className="mt-1 flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
              {c.industry && (
                <span className="inline-flex items-center gap-1">
                  <Tag className="size-3.5" aria-hidden />
                  {c.industry}
                </span>
              )}
              {c.size && (
                <span className="inline-flex items-center gap-1">
                  <Users className="size-3.5" aria-hidden />
                  {c.size}
                </span>
              )}
            </div>
          </div>
        </CardHeader>
      </Card>

      <Card className="col-span-full">
        <CardHeader>
          <CardTitle>Overview</CardTitle>
        </CardHeader>
        <CardContent>
          {c.overview ? (
            <p className="text-sm text-muted-foreground whitespace-pre-wrap">{c.overview}</p>
          ) : (
            <p className="text-sm text-muted-foreground">No overview available yet.</p>
          )}
        </CardContent>
      </Card>

      {/* 4.8 — the corpus's own read of this company */}
      <Card className="col-span-full">
        <CardHeader>
          <CardTitle>What the postings say</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {brief.data ? (
            <>
              {(brief.data.skills ?? []).length > 0 && (
                <div>
                  <p className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
                    Skills asked for
                  </p>
                  <div className="mt-1.5 flex flex-wrap gap-1.5">
                    {(brief.data.skills ?? []).map((s) => (
                      <Badge key={s.name} variant="secondary">
                        {s.name}
                        {s.count != null && (
                          <span className="ml-1 text-muted-foreground">×{s.count}</span>
                        )}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
              {(brief.data.interviewTopics ?? []).length > 0 && (
                <div>
                  <p className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
                    Interview topics
                  </p>
                  <p className="mt-1 text-sm">{brief.data.interviewTopics!.join(" · ")}</p>
                </div>
              )}
            </>
          ) : brief.isPending ? (
            <p className="text-sm text-muted-foreground">Reading the corpus…</p>
          ) : (
            <p className="text-sm text-muted-foreground">
              No postings in the corpus for this company yet.
            </p>
          )}
          <Button
            variant="outline"
            size="sm"
            loading={brief.isPending}
            onClick={() => brief.mutate({ company: c.name })}
          >
            Read the corpus
          </Button>
        </CardContent>
      </Card>

      <Card className="col-span-full">
        <CardHeader>
          <CardTitle>Tech Stack</CardTitle>
        </CardHeader>
        <CardContent>
          {(c.techStack ?? []).length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {(c.techStack ?? []).map((t) => (
                <Badge key={t} variant="secondary" className="gap-1">
                  <Code className="size-3" aria-hidden />
                  {t}
                </Badge>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No tech stack reported yet.</p>
          )}
        </CardContent>
      </Card>

      {(c.culture || c.interviewProcess) && (
        <Card className="col-span-full">
          <CardHeader>
            <CardTitle>Working here</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {c.culture && (
              <div className="space-y-1">
                <h4 className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
                  Culture
                </h4>
                <p className="text-sm text-muted-foreground whitespace-pre-wrap">{c.culture}</p>
              </div>
            )}
            {c.interviewProcess && (
              <div className="space-y-1">
                <h4 className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
                  Interview process
                </h4>
                <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                  {c.interviewProcess}
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      <Card className="col-span-full">
        <CardHeader>
          <CardTitle>Open Roles ({total})</CardTitle>
        </CardHeader>
        <CardContent>
          {openRoles.length > 0 ? (
            <>
              <ul className="space-y-2">
                {openRoles.map((job) => (
                  <RoleRow key={job.id} job={job} />
                ))}
              </ul>
              {total > openRoles.length && (
                <p className="mt-3 text-xs text-muted-foreground">
                  Showing the {openRoles.length} best-matching of {total} open roles.
                </p>
              )}
            </>
          ) : (
            <p className="text-sm text-muted-foreground">No open roles at the moment.</p>
          )}
        </CardContent>
      </Card>

      <Card className="col-span-full">
        <CardHeader>
          <CardTitle>Sources</CardTitle>
        </CardHeader>
        <CardContent>
          {(c.sources ?? []).length > 0 ? (
            <ul className="space-y-2">
              {(c.sources ?? []).map((s, i) => (
                <SourceRow key={`${s.type ?? "source"}-${i}`} source={s} />
              ))}
            </ul>
          ) : (
            <p className="text-sm text-muted-foreground">
              Nothing recorded where this profile came from yet.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

/**
 * One open role, as the board's own row shape (`JobListItem`) carries it: the title, where it is, and
 * the band when the posting named one — the same rule the job card follows, so a role with no salary
 * shows nothing rather than a placeholder.
 */
function RoleRow({ job }: { job: Job }) {
  const salary = formatSalary(job.salaryMin, job.salaryMax, job.salaryCurrency);
  return (
    <li>
      <Link
        href={`/jobs/${job.id}`}
        className="flex items-center justify-between gap-2 p-2 rounded-lg border border-border/50 hover:bg-muted/50 transition-colors"
      >
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium">{job.title}</p>
          <p className="truncate text-xs text-muted-foreground">
            {job.location && (
              <span className="inline-flex items-center gap-1">
                <MapPin className="size-3" aria-hidden />
                {job.location}
              </span>
            )}
          </p>
        </div>
        {salary && <span className="shrink-0 text-xs text-muted-foreground">{salary}</span>}
      </Link>
    </li>
  );
}

/**
 * One external fact's provenance. The wire carries a free jsonb object, so only the four names both
 * writers fill are rendered — a `type` badge and the first text field beside it. An object carrying
 * none of them still renders, as its type, rather than as raw JSON.
 */
function SourceRow({ source }: { source: CompanySource }) {
  const text = source.title ?? source.note;
  return (
    <li className="flex items-start gap-2 text-sm">
      {source.type && (
        <Badge variant="outline" className="shrink-0 text-2xs">
          {source.type}
        </Badge>
      )}
      <span className="min-w-0 flex-1 text-muted-foreground">{text}</span>
      {source.url && (
        <a
          href={source.url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex shrink-0 items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
        >
          Open
          <ExternalLink className="size-3" aria-hidden />
        </a>
      )}
    </li>
  );
}
