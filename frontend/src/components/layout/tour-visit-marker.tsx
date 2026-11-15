"use client";

import * as React from "react";
import { usePathname } from "next/navigation";
import { markTourVisited } from "@/lib/tour";

/**
 * The nine quests, part one (Epic 235).
 *
 * One effect, no UI: it checks the current room into the tour whenever the
 * reader walks into one of the nine. Reading the set back is the dashboard's
 * job; this is the only marker, mounted once in the authenticated shell.
 */
export function TourVisitMarker() {
  const pathname = usePathname();
  React.useEffect(() => {
    markTourVisited(pathname);
  }, [pathname]);
  return null;
}
