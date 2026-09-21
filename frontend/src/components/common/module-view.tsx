"use client";

import * as React from "react";
import type { UseQueryResult } from "@tanstack/react-query";
import Link from "next/link";
import { RefreshCw, Sparkles } from "lucide-react";
import { PageHeader } from "@/components/common/page-header";
import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { LoadingListSkeleton } from "@/components/common/loading-skeletons";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api/client";
import type { Page } from "@/lib/api/types";

/**
 * ModuleView — the shared async list shell for every (app) resource page.
 * Enforces: skeleton → content | 404 empty-state | error+retry. No fake data.
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
}: {
  title: string;
  description: string;
  query: UseQueryResult<Page<T>, unknown>;
  emptyHint: { title: string; description: string };
  ctaHref?: string;
  ctaLabel?: string;
  renderItem: (item: T) => React.ReactNode;
  actions?: React.ReactNode;
}) {
  const notFound = query.error instanceof ApiError && query.error.isNotFound;

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
              aria-label="Refresh list"
            >
              <RefreshCw aria-hidden />
              Refresh
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
            {notFound ? (
              <EmptyState
                icon={<Sparkles aria-hidden />}
                title={emptyHint.title}
                description={emptyHint.description}
                action={
                  ctaHref ? (
                    <Button variant="ai" size="sm" asChild>
                      <Link href={ctaHref}>{ctaLabel ?? "Open Copilot"}</Link>
                    </Button>
                  ) : (
                    <Button variant="outline" size="sm" onClick={() => query.refetch()}>
                      Try again
                    </Button>
                  )
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
                ctaHref ? (
                  <Button variant="ai" size="sm" asChild>
                    <Link href={ctaHref}>{ctaLabel ?? "Open Copilot"}</Link>
                  </Button>
                ) : undefined
              }
            />
          </CardContent>
        </Card>
      ) : (
        <div className="flex flex-col gap-2">{query.data.items.map(renderItem)}</div>
      )}
    </div>
  );
}
