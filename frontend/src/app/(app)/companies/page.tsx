"use client";

import * as React from "react";
import Link from "next/link";
import { Building2, Globe } from "lucide-react";
import { ModuleView } from "@/components/common/module-view";
import { Pagination } from "@/components/common/pagination";
import { lastPageOf } from "@/lib/page-window";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useCompanies } from "@/lib/hooks/resources";
import { useUrlState } from "@/lib/hooks/use-url-state";
import { useLocale } from "@/lib/i18n/locale-context";

// The route's own default window: `GET /companies` binds `size` with `defaultValue = "20"`, so
// this number asks for exactly what the server would have chosen anyway.
const PAGE_SIZE = 20;

// Module-level so `setUrl` (a `useCallback` keyed on this object) is stable across renders.
const PAGE_DEFAULTS: { page: number } = { page: 0 };

export default function CompaniesPage() {
  const { t } = useLocale();
  // The page index lives in the URL, so a reload or a shared list link opens the same window.
  const [state, setUrl] = useUrlState<{ page: number }>(
    PAGE_DEFAULTS,
    { numericKeys: ["page"] }
  );
  const companies = useCompanies({ page: state.page, size: PAGE_SIZE });

  const total = companies.data?.total ?? 0;
  // A past-the-end page is an empty window over a real total, not an empty list: the answer's
  // own window is the divisor (`data.size`), so the URL is corrected to the last page that
  // exists -- `lastPageOf` (lib/page-window.ts) is that rule in one place. A layout effect,
  // because the stale commit paints its empty copy first -- React flushes this update before
  // the browser paints, so the wrong screen is replaced, not seen.
  const lastPage = companies.data ? lastPageOf(total, companies.data.size) : 0;
  React.useLayoutEffect(() => {
    if (companies.data && state.page > lastPage) setUrl({ page: lastPage });
  }, [companies.data, state.page, lastPage, setUrl]);

  return (
    <ModuleView
      title={t("companies.title")}
      description={t("companies.description")}
      query={companies}
      emptyHint={{
        title: t("companies.noneResearched"),
        description: t("companies.noneResearchedDescription"),
      }}
      ctaHref="/copilot"
      ctaLabel={t("companies.researchOne")}
      footer={
        total > PAGE_SIZE && (
          <Pagination
            page={companies.data?.page ?? state.page}
            size={PAGE_SIZE}
            total={total}
            label={t("companies.paginationLabel")}
            onPageChange={(page) => {
              setUrl({ page });
              window.scrollTo({ top: 0, behavior: "smooth" });
            }}
          />
        )
      }
      renderItem={(c) => (
        <Card key={c.id}>
          <CardContent className="flex items-center gap-3">
            {c.logoUrl ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={c.logoUrl} alt="" className="size-9 rounded-lg border border-border object-contain p-1" />
            ) : (
              <span className="flex size-9 items-center justify-center rounded-lg bg-muted text-muted-foreground">
                <Building2 className="size-4.5" aria-hidden />
              </span>
            )}
            <div className="min-w-0 flex-1">
              {/* The profile page is where the researched detail lives, so the name is the link —
                  and it is a real one: `openRoleCount` says whether there is anything behind it. */}
              <Link
                href={`/companies/${c.id}`}
                className="truncate text-sm font-medium hover:underline focus-visible:ring-[3px] focus-visible:ring-ring/35 rounded-sm"
              >
                {c.name}
              </Link>
              <p className="truncate text-xs text-muted-foreground">
                {[c.industry, c.size].filter(Boolean).join(" · ") || t("companies.profilePending")}
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-1.5">
              {typeof c.openRoleCount === "number" && (
                <Badge variant="secondary" className="text-2xs">
                  {c.openRoleCount}{" "}
                  {c.openRoleCount === 1
                    ? t("companies.role")
                    : t("companies.roles")}
                </Badge>
              )}
              {(c.techStack ?? []).slice(0, 3).map((t) => (
                <Badge key={t} variant="outline" className="text-2xs">
                  {t}
                </Badge>
              ))}
              {c.website && (
                <a
                  href={c.website}
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label={t("companies.websiteLabel", { name: c.name })}
                  className="rounded-md p-1 text-muted-foreground hover:text-foreground focus-visible:ring-[3px] focus-visible:ring-ring/35"
                >
                  <Globe className="size-4" aria-hidden />
                </a>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    />
  );
}
