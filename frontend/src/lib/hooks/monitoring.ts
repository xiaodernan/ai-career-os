"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import {
  type NormalizedPage,
  normalizeHealthReport,
  normalizeNightlyReport,
  normalizeNightlyVerdict,
  normalizePage,
} from "@/lib/api/normalize";
import type {
  DeploymentHealth,
  NightlyReport,
  NightlyVerdict,
  ServiceResilience,
  ServiceTopology,
} from "@/lib/api/types";

/**
 * Production monitoring (16.1): agent health, cost, and regression detection.
 */
export function useHealthReport() {
  return useQuery({
    queryKey: ["monitoring", "health-report"],
    queryFn: async () => normalizeHealthReport(await api.get<unknown>(endpoints.monitoringHealthReport)),
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

/** Spring Cloud circuit breaker states for the ai-service bridge (Epic 105). */
export function useServiceResilience() {
  return useQuery({
    queryKey: ["system", "resilience"],
    queryFn: async (): Promise<ServiceResilience> =>
      (await api.get<unknown>(endpoints.systemResilience)) as ServiceResilience,
    staleTime: 30_000,
  });
}

/** The engine fleet through the backend's public dependency report (Epic 108.23). */
export function useDeploymentHealth() {
  return useQuery({
    queryKey: ["system", "deployment-health"],
    queryFn: async (): Promise<DeploymentHealth> =>
      (await api.get<unknown>(endpoints.health)) as DeploymentHealth,
    staleTime: 30_000,
  });
}
