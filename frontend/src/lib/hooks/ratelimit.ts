"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import type { RateLimitStatus } from "@/lib/api/types";

/**
 * Rate-limit status (16.2): the current rate-limit configuration and the caller's
 * current bucket usage.
 */
export function useRateLimitStatus() {
  return useQuery({
    queryKey: ["rate-limit", "status"],
    queryFn: async () => (await api.get<unknown>(endpoints.rateLimitStatus)) as RateLimitStatus,
    refetchInterval: 30_000,
  });
}
