import { Skeleton } from "@/components/ui/skeleton";
import { LoadingCardSkeleton } from "@/components/common/loading-skeletons";

/**
 * Route-segment fallback for the signed-in area. It covers the one gap the
 * pages' own react-query skeletons cannot: the moment the router has the URL
 * but the next page's code chunk is still in flight, the previous screen
 * would otherwise sit frozen with no sign the click registered.
 */
export default function Loading() {
  return (
    <div className="space-y-6" role="status" aria-label="Loading page">
      <div className="space-y-2">
        <Skeleton className="h-8 w-56" />
        <Skeleton className="h-4 w-80 max-w-full" />
      </div>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        <LoadingCardSkeleton />
        <LoadingCardSkeleton />
        <LoadingCardSkeleton />
      </div>
      <span className="sr-only">Loading…</span>
    </div>
  );
}
