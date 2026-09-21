import * as React from "react";
import { cn } from "@/lib/utils";
import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent } from "@/components/ui/card";

/**
 * Loading skeletons composing the real dashboard shapes — the same
 * shimmer language as ProcessingSteps.
 */

export function LoadingListSkeleton({
  rows = 4,
  className,
  showAvatars = true,
}: {
  rows?: number;
  className?: string;
  showAvatars?: boolean;
}) {
  return (
    <div role="status" aria-label="Loading" className={cn("flex flex-col", className)}>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex items-center gap-3 border-b border-border/50 py-3 last:border-0">
          {showAvatars && <Skeleton className="size-9 rounded-lg" />}
          <div className="flex-1 space-y-1.5">
            <Skeleton className="h-3.5 w-2/5" />
            <Skeleton className="h-3 w-3/5" />
          </div>
          <Skeleton className="h-6 w-16 rounded-full" />
        </div>
      ))}
      <span className="sr-only">Loading…</span>
    </div>
  );
}

export function LoadingCardSkeleton({ className }: { className?: string }) {
  return (
    <Card className={cn("", className)}>
      <div className="space-y-3">
        <Skeleton className="h-3.5 w-1/3" />
        <Skeleton className="h-7 w-1/2" />
        <Skeleton className="h-3 w-2/3" />
      </div>
    </Card>
  );
}

export function LoadingMetricGridSkeleton({ count = 4 }: { count?: number }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4" aria-hidden>
      {Array.from({ length: count }).map((_, i) => (
        <LoadingCardSkeleton key={i} />
      ))}
    </div>
  );
}

/** Ring + text row — job cards, match summaries. */
export function LoadingJobCardSkeleton({ count = 3 }: { count?: number }) {
  return (
    <div className="flex flex-col gap-3" aria-label="Loading jobs" role="status">
      {Array.from({ length: count }).map((_, i) => (
        <Card key={i} className="flex-row items-center gap-4 p-4">
          <Skeleton className="size-14 rounded-full" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-4 w-1/3" />
            <Skeleton className="h-3 w-1/4" />
            <div className="flex gap-1.5 pt-1">
              {Array.from({ length: 4 }).map((_, j) => (
                <Skeleton key={j} className="h-5 w-16 rounded-full" />
              ))}
            </div>
          </div>
          <Skeleton className="h-8 w-20 rounded-lg" />
        </Card>
      ))}
      <span className="sr-only">Loading…</span>
    </div>
  );
}

/** Kanban column skeleton for the applications board. */
export function LoadingKanbanSkeleton({ columns = 4, rows = 2 }: { columns?: number; rows?: number }) {
  return (
    <div
      className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4"
      role="status"
      aria-label="Loading pipeline"
    >
      {Array.from({ length: columns }).map((_, c) => (
        <div key={c} className="space-y-2 rounded-xl border border-border/60 bg-muted/30 p-3">
          <div className="flex items-center justify-between">
            <Skeleton className="h-3.5 w-20" />
            <Skeleton className="h-4 w-6 rounded-full" />
          </div>
          {Array.from({ length: rows }).map((_, r) => (
            <div key={r} className="space-y-2 rounded-lg border border-border/60 bg-card p-3">
              <Skeleton className="h-3.5 w-3/4" />
              <Skeleton className="h-3 w-1/2" />
            </div>
          ))}
        </div>
      ))}
      <span className="sr-only">Loading…</span>
    </div>
  );
}

/** Chat transcript skeleton: alternating bubbles. */
export function LoadingChatSkeleton({ turns = 2 }: { turns?: number }) {
  return (
    <div className="flex flex-col gap-4" role="status" aria-label="Loading conversation">
      {Array.from({ length: turns }).map((_, i) => (
        <div key={i} className={cn("flex flex-col gap-2", i % 2 === 1 && "items-end")}>
          <Skeleton className={cn("h-3.5", i % 2 === 0 ? "w-2/3" : "w-1/3")} />
          <Skeleton className={cn("h-3", i % 2 === 0 ? "w-1/2" : "w-1/4")} />
          <Skeleton className={cn("h-3", i % 2 === 0 ? "w-3/5" : "w-1/5")} />
        </div>
      ))}
      <span className="sr-only">Loading…</span>
    </div>
  );
}

/** Two-column detail skeleton: header, ring, section blocks. */
export function LoadingDetailSkeleton() {
  return (
    <div className="space-y-6" role="status" aria-label="Loading details">
      <div className="flex items-start gap-4">
        <Skeleton className="size-12 rounded-xl" />
        <div className="flex-1 space-y-2">
          <Skeleton className="h-6 w-2/5" />
          <Skeleton className="h-4 w-1/4" />
        </div>
        <Skeleton className="size-16 rounded-full" />
      </div>
      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardContent className="space-y-3">
            <Skeleton className="h-4 w-1/3" />
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-3 w-full" />
            ))}
          </CardContent>
        </Card>
        <Card>
          <CardContent className="space-y-3">
            <Skeleton className="h-4 w-1/2" />
            <Skeleton className="h-20 w-full rounded-lg" />
            <Skeleton className="h-20 w-full rounded-lg" />
          </CardContent>
        </Card>
      </div>
      <span className="sr-only">Loading…</span>
    </div>
  );
}

/** Table skeleton for sources / activity / companies. */
export function LoadingTableSkeleton({ rows = 5, cols = 4 }: { rows?: number; cols?: number }) {
  return (
    <div className="flex flex-col" role="status" aria-label="Loading table">
      <div className="flex gap-4 border-b border-border/60 px-4 py-2.5">
        {Array.from({ length: cols }).map((_, i) => (
          <Skeleton key={i} className="h-3 w-20" />
        ))}
      </div>
      {Array.from({ length: rows }).map((_, r) => (
        <div key={r} className="flex items-center gap-4 border-b border-border/40 px-4 py-3 last:border-0">
          {Array.from({ length: cols }).map((_, i) => (
            <Skeleton key={i} className={cn("h-3.5", i === 0 ? "w-1/3" : "w-16")} />
          ))}
        </div>
      ))}
      <span className="sr-only">Loading…</span>
    </div>
  );
}
