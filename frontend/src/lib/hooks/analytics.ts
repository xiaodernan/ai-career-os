"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import type { InsightDigest, PipelineFunnel, ResponseRate } from "@/lib/api/types";
import type { Locale } from "@/lib/i18n/translations";

/**
 * The weekly insight digest (15.3): stalled applications, live stage mix, and
 * headline rates, composed by the ai-service's analytics engine.
 *
 * `locale` is the reader's language. The digest's signals are the only words the
 * engine writes into this answer, so the page says which language it is showing;
 * and the locale is part of the query key, because switching the language must
 * refetch rather than reuse the other language's sentences.
 */
export function useInsightDigest(locale: Locale) {
  return useQuery({
    queryKey: ["analysis", "insight-digest", locale],
    queryFn: async () =>
      (await api.get<unknown>(endpoints.analysisInsightDigest, { locale })) as InsightDigest,
  });
}

/**
 * 15.1 — the pipeline funnel: how many applications reached each stage, and
 * where the leak is.
 */
export function usePipelineFunnel() {
  return useQuery({
    queryKey: ["analysis", "pipeline-funnel"],
    queryFn: async () => (await api.get<unknown>(endpoints.analysisPipelineFunnel)) as PipelineFunnel,
  });
}

/**
 * 15.2 — the reply / interview / offer rates and the per-stage durations.
 * A rejection counts as a response: a no is still an answer.
 */
export function useResponseRate() {
  return useQuery({
    queryKey: ["analysis", "response-rate"],
    queryFn: async () => (await api.get<unknown>(endpoints.analysisResponseRate)) as ResponseRate,
  });
}
