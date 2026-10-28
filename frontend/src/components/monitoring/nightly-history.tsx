"use client";

import * as React from "react";
import { CalendarCheck, ExternalLink } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/common/error-state";
import { Pagination } from "@/components/common/pagination";
import { relativeTime } from "@/lib/format";
import { useLocale } from "@/lib/i18n/locale-context";
import { safeHref } from "@/lib/safe-href";
import { useNightlyReports } from "@/lib/hooks/monitoring";

/**
 * The deployment's own verification history (roadmap 20.1).
 *
 * The nightly job posts one record when it ends — the backend suites, the eval harness
 * and the export check, each with the numbers it measured — and this card is where a
 * reader asks "did last Tuesday's night pass?" weeks after the runner's logs expired.
 *
 * The card keeps the same three quiet promises the other list panels keep: the empty
 * copy speaks only once the list has answered, a failed read is named rather than drawn
 * as an empty history, and a step's measurement is shown only when the job wrote one.
 */

// The route's own default window: `GET /monitoring/nightly-reports` binds `size` with
// `defaultValue = "10"`, so this number asks for exactly what the server would have chosen.
const PAGE_SIZE = 10;

function badgeVariant(status: string): "success" | "destructive" | "outline" {
  if (status === "passed") return "success";
  if (status === "failed") return "destructive";
  return "outline";
}

export function NightlyHistory() {
  const { t, locale } = useLocale();
  const [page, setPage] = React.useState(0);
  const reports = useNightlyReports({ page, size: PAGE_SIZE });
  const rows = reports.data?.items ?? [];
  const total = reports.data?.total ?? 0;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <CalendarCheck className="size-4" aria-hidden />
          {t("monitoring.nightlyTitle")}
        </CardTitle>
        <CardDescription>{t("monitoring.nightlyDescription")}</CardDescription>
      </CardHeader>
      <CardContent>
        {reports.isPending ? (
          <Skeleton className="h-24 rounded-lg" />
        ) : reports.isError ? (
          <ErrorState
            title={t("monitoring.nightlyUnavailable")}
            error={reports.error}
            onRetry={() => void reports.refetch()}
            retrying={reports.isFetching}
          />
        ) : rows.length === 0 ? (
          <p className="text-sm text-muted-foreground">{t("monitoring.nightlyEmpty")}</p>
        ) : (
          <ul className="space-y-2">
            {rows.map((row) => (
              <li key={row.id} className="rounded-lg border border-border/70 p-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex min-w-0 flex-wrap items-center gap-2">
                    <Badge variant={badgeVariant(row.status)}>
                      {row.status === "passed"
                        ? t("monitoring.nightlyPassed")
                        : row.status === "failed"
                          ? t("monitoring.nightlyFailed")
                          : row.status}
                    </Badge>
                    <span className="text-xs text-muted-foreground">
                      {relativeTime(row.startedAt, locale)}
                    </span>
                    {row.commitSha && (
                      <code className="rounded bg-muted px-1.5 py-0.5 text-[11px] text-muted-foreground">
                        {row.commitSha.slice(0, 7)}
                      </code>
                    )}
                  </div>
                  {row.runUrl && safeHref(row.runUrl) && (
                    <a
                      href={safeHref(row.runUrl)}
                      target="_blank"
                      rel="noreferrer"
                      className="flex items-center gap-1 text-xs text-primary hover:underline"
                    >
                      {t("monitoring.nightlyOpenRun")}
                      <ExternalLink className="size-3" aria-hidden />
                    </a>
                  )}
                </div>
                {row.steps.length > 0 && (
                  <div className="mt-2 flex flex-wrap items-center gap-1.5">
                    {row.steps.map((step, index) => (
                      <Badge
                        key={`${step.name}-${index}`}
                        variant={badgeVariant(step.status)}
                        title={step.detail ?? undefined}
                      >
                        {step.name}
                      </Badge>
                    ))}
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
        {total > PAGE_SIZE && (
          <div className="mt-4 flex justify-end">
            <Pagination
              page={reports.data?.page ?? page}
              size={PAGE_SIZE}
              total={total}
              label={t("monitoring.nightlyPagination")}
              onPageChange={(next) => {
                setPage(next);
                window.scrollTo({ top: 0, behavior: "smooth" });
              }}
            />
          </div>
        )}
      </CardContent>
    </Card>
  );
}
