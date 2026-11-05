"use client";

import * as React from "react";
import Link from "next/link";
import { Building2, Globe, Search } from "lucide-react";
import { ModuleView } from "@/components/common/module-view";
import { Pagination } from "@/components/common/pagination";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { lastPageOf } from "@/lib/page-window";
import { safeHref } from "@/lib/safe-href";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useCompanies } from "@/lib/hooks/resources";
import { useUrlState } from "@/lib/hooks/use-url-state";
import { useLocale } from "@/lib/i18n/locale-context";

// The route's own default window: `GET /companies` binds `size` with `defaultValue = "20"`, so
// this number asks for exactly what the server would have chosen anyway.
const PAGE_SIZE = 20;

// Module-level so `setUrl` (a `useCallback` keyed on this object) is stable across renders.
const PAGE_DEFAULTS: { page: number; q?: string } = { page: 0, q: undefined };

export default function CompaniesPage() {
  const { t } = useLocale();
  // The page index and the words both live in the URL, so a reload or a shared link opens the
  // same window of the same question -- the rule the replies board set (49.1) and the narrowed
  // interview list follows (57.1).
  const [state, setUrl] = useUrlState<{ page: number; q?: string }>(
    PAGE_DEFAULTS,
    { numericKeys: ["page"] }
  );
  // The box holds what the reader is typing; the page holds what was asked. Keeping them apart is
  // what makes the address bar the only answer to "what is this list showing", so a back button or
  // a pasted link redraws the words in the box as well as the rows under it.
  const [draft, setDraft] = React.useState(state.q ?? "");
  React.useEffect(() => setDraft(state.q ?? ""), [state.q]);
  const ask = (value: string) => setUrl({ q: value.trim() || undefined, page: 0 });
  const companies = useCompanies({ page: state.page, size: PAGE_SIZE, q: state.q });

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
      // The question the route has always answered (`?q=`) and the screen never asked. It is the
      // server's search rather than a filter over this page: the pager below counts the matches,
      // so page two of a word is the second page of the matches -- and since 58.1 the words are
      // read as characters, which is what lets a name carrying a percent or an underscore be found
      // by spelling it.
      actions={
        <form
          role="search"
          className="flex items-center gap-2"
          onSubmit={(event) => {
            event.preventDefault();
            ask(draft);
          }}
        >
          <div className="relative">
            <Search
              aria-hidden
              className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground"
            />
            <Input
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              placeholder={t("companies.searchPlaceholder")}
              aria-label={t("companies.searchLabel")}
              autoComplete="off"
              className="w-40 pl-9 sm:w-60"
            />
          </div>
          <Button type="submit" size="sm" variant="outline">
            {t("chrome.search")}
          </Button>
          {state.q ? (
            <Button
              type="button"
              size="sm"
              variant="ghost"
              onClick={() => {
                setDraft("");
                ask("");
              }}
            >
              {t("companies.clearSearch")}
            </Button>
          ) : null}
        </form>
      }
      query={companies}
      // Two different empties: a catalog nobody has researched, and a catalog full of companies
      // none of which is named what the reader typed. The second one must not send the reader off
      // to research a company -- the replies board learned the same lesson in 49.2.
      emptyHint={
        state.q
          ? {
              title: t("companies.noMatch", { query: state.q }),
              description: t("companies.noMatchDescription"),
              action: (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setDraft("");
                    ask("");
                  }}
                >
                  {t("companies.clearSearch")}
                </Button>
              ),
            }
          : {
              title: t("companies.noneResearched"),
              description: t("companies.noneResearchedDescription"),
            }
      }
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
              {/* Asked twice because a row renderer has no place to keep the answer: the
                  button disappears when the stored value cannot open a page. */}
              {safeHref(c.website) && (
                <a
                  href={safeHref(c.website)}
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
