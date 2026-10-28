"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import { list as listOf, normalizeWeeklyDigest } from "@/lib/api/normalize";
import type { InsightDigest, PipelineFunnel, ResponseRate, WeeklyDigest } from "@/lib/api/types";
import { fail } from "@/lib/hooks/failure";
import { translate } from "@/lib/i18n/locale-context";
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

/**
 * The letters the night has filed (19.4): one per week, newest first. Reading history is
 * not a second computation -- each letter is the digest as it was composed that week.
 */
export function useWeeklyDigests() {
  return useQuery({
    queryKey: ["analysis", "weekly-digests"],
    queryFn: async (): Promise<WeeklyDigest[]> =>
      listOf<unknown>(await api.get<unknown>(endpoints.digests)).map(normalizeWeeklyDigest),
  });
}

/**
 * 19.4 -- compose the current week's letter now. The answer is the filed letter, but the
 * page draws the list, so the write refetches it rather than splicing one row into a week
 * that may already have had a letter (which the server refreshes in place).
 */
export function useComposeWeeklyDigest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (): Promise<WeeklyDigest> =>
      normalizeWeeklyDigest(
        await api.request<unknown>(endpoints.digestsRun, { method: "POST" })
      ),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["analysis", "weekly-digests"] }),
    onError: fail(translate("analysis.weeklyActionFailed") ?? "Couldn't compose the letter."),
  });
}
