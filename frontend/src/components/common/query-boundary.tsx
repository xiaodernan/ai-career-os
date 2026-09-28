"use client";

import * as React from "react";
import type { UseQueryResult } from "@tanstack/react-query";
import { PlugZap, RotateCcw } from "lucide-react";
import { cn } from "@/lib/utils";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { EmptyState, type EmptyStateProps } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { LoadingListSkeleton } from "@/components/common/loading-skeletons";
import { ApiError } from "@/lib/api/client";
import { missingEndpointMessage } from "@/lib/api/missing-endpoint";

/**
 * QueryBoundary — the single async contract used by every surface:
 *   pending → skeleton · error → ErrorState(retry) · 404/empty → designed
 *   EmptyState(with next action) · success → children(data).
 * Nothing renders "Loading…" and nothing renders invented data.
 */

export function isEndpointMissing(error: unknown): boolean {
  return error instanceof ApiError && (error.isNotFound || error.status === 501);
}

/**
 * Whether a settled payload has no rows to show.
 *
 * A list can arrive as a bare array or as the `{items,total}` shape `normalizePage`
 * builds, and the page-shaped one stays an object even when the server returned zero
 * rows — so testing only for `null` and `[]` meant every `empty` state written for a
 * list screen was unreachable: the boundary rendered `children` over an empty `<ul>`
 * and the designed "Nothing here yet → next action" never appeared.
 *
 * An object without an `items` array is a detail payload, not an empty list, and is
 * never guessed to be empty.
 */
export function isEmptyPage(data: unknown): boolean {
  if (data == null) return true;
  if (Array.isArray(data)) return data.length === 0;
  const items = (data as { items?: unknown }).items;
  return Array.isArray(items) && items.length === 0;
}

export interface QueryBoundaryProps<T> {
  query: UseQueryResult<T, unknown>;
  children: (data: NonNullable<T>) => React.ReactNode;
  /** Shown while pending — pass a shape-matched skeleton. */
  skeleton?: React.ReactNode;
  /** Shown for 200-with-no-rows *and* for a missing endpoint. */
  empty: EmptyStateProps;
  /** Extra guidance override used when the endpoint itself is absent. */
  notLive?: Partial<EmptyStateProps>;
  /** Rendered instead of the plain children wrapper (e.g. a grid). */
  className?: string;
  /** Wrap states in a Card (default true). Content is never wrapped. */
  boxed?: boolean;
  /** Hide everything until settled and let the caller animate in. */
  reserveHeight?: boolean;
}

export function QueryBoundary<T>({
  query,
  children,
  skeleton,
  empty,
  notLive,
  className,
  boxed = true,
}: QueryBoundaryProps<T>) {
  const retry = () => void query.refetch();
  const emptyIcon = empty.icon ?? <PlugZap aria-hidden />;

  const body = (() => {
    if (query.isPending) return skeleton ?? <LoadingListSkeleton />;
    if (query.isError) {
      if (isEndpointMissing(query.error)) {
        return (
          <EmptyState
            {...empty}
            icon={emptyIcon}
            {...notLive}
            description={notLive?.description ?? missingEndpointMessage()}
            action={
              <Button variant="outline" size="sm" onClick={retry}>
                <RotateCcw aria-hidden />
                Check again
              </Button>
            }
          />
        );
      }
      return <ErrorState error={query.error} onRetry={retry} retrying={query.isFetching} />;
    }
    if (isEmptyPage(query.data)) return <EmptyState {...empty} icon={emptyIcon} />;
    // `isEmptyPage` judges content, not types, so it cannot narrow `T` for the compiler;
    // the predicate's own rule guarantees a non-null payload reached this line.
    return children(query.data as NonNullable<T>);
  })();

  if (!boxed) return <>{body}</>;
  const settled = !query.isPending && !query.isError && !isEmptyPage(query.data);
  if (settled) return <div className={className}>{body}</div>;
  return (
    <Card>
      <CardContent>{body}</CardContent>
    </Card>
  );
}

/**
 * SectionBoundary — same contract for a widget inside an already-carded
 * section (dashboard tiles, sidebars). Never adds its own card.
 */
export function SectionBoundary<T>({
  query,
  children,
  skeleton,
  empty,
  notLive,
}: Omit<QueryBoundaryProps<T>, "boxed" | "className">) {
  return (
    <QueryBoundary
      query={query}
      skeleton={skeleton}
      empty={empty}
      notLive={notLive}
      boxed={false}
      className=""
    >
      {children}
    </QueryBoundary>
  );
}

/** Inline "endpoint not live" hint for secondary widgets. */
export function EndpointOffline({ name, className }: { name: string; className?: string }) {
  return (
    <p className={cn("flex items-center gap-1.5 text-xs text-muted-foreground", className)}>
      <PlugZap className="size-3.5 shrink-0" aria-hidden />
      {name} isn&apos;t connected yet — it will appear as soon as the API serves it.
    </p>
  );
}
