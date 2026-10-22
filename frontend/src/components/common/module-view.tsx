"use client";

import * as React from "react";
import type { UseQueryResult } from "@tanstack/react-query";
import Link from "next/link";
import { PlugZap, RefreshCw, RotateCcw, Sparkles } from "lucide-react";
import { PageHeader } from "@/components/common/page-header";
import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { LoadingListSkeleton } from "@/components/common/loading-skeletons";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api/client";
import { missingEndpointMessage } from "@/lib/api/missing-endpoint";
import { useLocale } from "@/lib/i18n/locale-context";
import type { Page } from "@/lib/api/types";

/**
 * ModuleView — the shared async list shell for every (app) resource page.
 * Enforces: skeleton → content | 404 not-live-state | error+retry. No fake data.
 *
 * The 404 is read by its **code**, not by its status. A 404 is two different
 * answers: the route is not served (`NOT_FOUND`), or the route is served and
 * the record it reads is gone (one code per record). Reporting the first as
 * an empty list is a false claim about the product, and so is reporting the
 * second as one -- the record is gone, and the reader can do something about
 * that. So the code decides: a route that is not served gets the not-live
 * state, and everything else gets the error surface, which shows the code's
 * own sentence.
 */
export function ModuleView<T>({
  title,
  description,
  query,
  emptyHint,
  ctaHref,
  ctaLabel,
  renderItem,
  actions,
  footer,
  children,
}: {
  title: string;
  description: string;
  query: UseQueryResult<Page<T>, unknown>;
  emptyHint: { title: string; description: string; action?: React.ReactNode };
  ctaHref?: string;
  ctaLabel?: string;
  /** Rendered under the list once the query has data and rows survive the empty check --
   * the slot a pager takes (companies, #222). Opt-in: a consumer that passes none sees
   * exactly the layout it always had. */
  footer?: React.ReactNode;
  /** Row renderer for the default list layout. Pages that render their own shape
   * (a board, a grid) pass `children` instead. */
  renderItem?: (item: T) => React.ReactNode;
  actions?: React.ReactNode;
  /** Replaces the list layout once the query has data. Empty still shows `emptyHint`,
   * so a board keeps the same "nothing here yet + call to action" contract. */
  children?: React.ReactNode;
}) {
  const { t } = useLocale();
  const routeMissing = query.error instanceof ApiError && query.error.code === "NOT_FOUND";

  return (
    <div className="space-y-6">
      <PageHeader
        title={title}
        description={description}
        actions={
          <>
            {actions}
            <Button
              variant="outline"
              size="sm"
              onClick={() => query.refetch()}
              loading={query.isFetching}
              aria-label={t("chrome.refreshList")}
            >
              <RefreshCw aria-hidden />
              {t("common.refresh")}
            </Button>
          </>
        }
      />

      {query.isPending ? (
        <Card>
          <CardContent className="px-3">
            <LoadingListSkeleton rows={5} />
          </CardContent>
        </Card>
      ) : query.isError ? (
        <Card>
          <CardContent>
            {routeMissing ? (
              <EmptyState
                icon={<PlugZap aria-hidden />}
                title={t("common.notLiveTitle")}
                description={missingEndpointMessage()}
                action={
                  <Button variant="outline" size="sm" onClick={() => query.refetch()}>
                    <RotateCcw aria-hidden />
                    {t("common.checkAgain")}
                  </Button>
                }
              />
            ) : (
              <ErrorState error={query.error} onRetry={() => query.refetch()} />
            )}
          </CardContent>
        </Card>
      ) : !query.data?.items.length ? (
        <Card>
          <CardContent>
            <EmptyState
              icon={<Sparkles aria-hidden />}
              title={emptyHint.title}
              description={emptyHint.description}
              action={
                emptyHint.action ??
                (ctaHref ? (
                  <Button variant="ai" size="sm" asChild>
                    <Link href={ctaHref}>{ctaLabel ?? t("common.openCopilot")}</Link>
                  </Button>
                ) : undefined)
              }
            />
          </CardContent>
        </Card>
      ) : (
        <div className="flex flex-col gap-2">
          {children ?? query.data.items.map((item) => renderItem?.(item))}
          {footer}
        </div>
      )}
    </div>
  );
}
