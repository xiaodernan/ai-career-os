import * as React from "react";
import { cn } from "@/lib/utils";
import { Skeleton } from "@/components/ui/skeleton";
import { Card } from "@/components/ui/card";

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
