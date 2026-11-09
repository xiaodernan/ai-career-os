"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import {
  normalizeNightlyReport,
  normalizeNightlyVerdict,
  normalizePage,
  type NormalizedPage,
} from "@/lib/api/normalize";
import type { HealthReport, NightlyReport, NightlyVerdict, ServiceTopology } from "@/lib/api/types";

/**
 * Production monitoring (16.1): agent health, cost, and regression detection.
 */
export function useHealthReport() {
  return useQuery({
    queryKey: ["monitoring", "health-report"],
    queryFn: async () => (await api.get<unknown>(endpoints.monitoringHealthReport)) as HealthReport,
  });
}

/**
 * The deployment's own nightly verification, newest first (roadmap 20.1). The window
 * defaults to the route's own 10, so the first visit asks for exactly the page the
 * server would have chosen anyway.
 */
export function useNightlyReports(params?: { page?: number; size?: number }) {
  return useQuery({
    queryKey: ["monitoring", "nightly-reports", params],
    queryFn: async (): Promise<NormalizedPage<NightlyReport>> =>
      normalizePage(
        await api.get<unknown>(endpoints.monitoringNightlyReports, { size: 10, ...(params ?? {}) }),
        normalizeNightlyReport
      ),
  });
}

/**
 * The install's verdict (roadmap 20.2): one answer instead of a page. The card draws the
 * history; this asks separately whether the history itself is the news, so a stopped
 * cadence is visible even when the newest row looks fine.
 */
export function useNightlyVerdict() {
  return useQuery({
    queryKey: ["monitoring", "nightly-verdict"],
    queryFn: async (): Promise<NightlyVerdict> =>
      normalizeNightlyVerdict(await api.get<unknown>(endpoints.monitoringNightlyVerdict)),
  });
}

/**
 * The fleet the backend can see (roadmap 100). It answers the same `DiscoveryClient` the
 * load balancer reads, so the card describes the routing table rather than a second
 * inventory. Deployment-wide, not per user; a short stale window is enough because the
 * registry itself answers from a lease cache.
 */
export function useServiceTopology() {
  return useQuery({
    queryKey: ["system", "topology"],
    queryFn: async (): Promise<ServiceTopology> =>
      (await api.get<unknown>(endpoints.systemTopology)) as ServiceTopology,
    staleTime: 30_000,
  });
}
