"use client";

import { useRouter } from "next/navigation";
import { useCallback } from "react";

/**
 * Warm a route before the reader clicks it, on hover and on keyboard focus.
 *
 * Next's Link auto-prefetches on hover in production but not on keyboard
 * focus -- same gap the sidebar's warm-on-intent closes for the nav (Epic 123).
 * The job list's row link stretches over the whole card, so hover and focus
 * are exactly where the reader's intent first shows: this covers the hottest
 * detail entry in the product (`/jobs/[id]`) and the resume list's two doors.
 *
 * The prefetch itself is idempotent -- calling it twice per gesture is free --
 * so the handlers layer on top of whatever the framework already does.
 */
export function useWarmLink() {
  const router = useRouter();
  return useCallback(
    (href: string) => () => router.prefetch(href),
    [router],
  );
}
