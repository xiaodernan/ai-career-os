"use client";

import { notFound, useParams } from "next/navigation";
import Link from "next/link";
import { Building2, Globe, Tag, Code, Users, MapPin, ExternalLink } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useCompany } from "@/lib/hooks/resources";
import { formatSalary } from "@/lib/format";
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

  if (company.isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <div className="h-8 w-1/4 animate-pulse bg-muted rounded" />
          <div className="h-4 w-1/2 animate-pulse bg-muted rounded" />
        </div>
        <div className="space-y-4">
          <div className="h-20 animate-pulse bg-muted rounded-xl" />
          <div className="h-8 w-1/2 animate-pulse bg-muted rounded" />
          <div className="h-8 w-1/4 animate-pulse bg-muted rounded" />
        </div>
      </div>
    );
  }

  // An id the API does not know is a 404 from the backend (isError), so this is the honest screen
  // for it -- the guard used to test the shape of a response body, which the client had already
  // unwrapped.
  if (company.isError || !company.data) {
    notFound();
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
