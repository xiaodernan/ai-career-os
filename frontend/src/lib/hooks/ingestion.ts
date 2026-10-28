"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import { normalizeIngestionRunDetail } from "@/lib/api/normalize";
import { fail } from "@/lib/hooks/failure";
import { translate } from "@/lib/i18n/locale-context";
import type {
  IngestPlan,
  IngestionRunDetail,
  ParsedFeed,
  PostingCollection,
  FreshnessSweep,
} from "@/lib/api/types";

/**
 * Job ingestion (14.2-14.3): parse a feed, deduplicate it against the corpus,
 * sweep it for freshness, and build one create/update/close plan.
 *
 * The bodies are built by named helpers so the wire shape is written down in
 * one place per route instead of being spread across the call sites.
 */

/** 14.2 — the feed to parse. */
function parseBody(feed: string, source?: string): { feed: string; source?: string } {
  return { feed, source };
}

/** 14.3 — the batch to deduplicate. */
function dedupeBody(postings: unknown[]): { postings: unknown[] } {
  return { postings };
}

/** 14.3 — the corpus to sweep, with the caller's windows when it named any. */
function sweepBody(
  postings: unknown[],
  maxAgeDays?: number,
  staleSeenDays?: number
): { postings: unknown[]; maxAgeDays?: number; staleSeenDays?: number } {
  return { postings, maxAgeDays, staleSeenDays };
}

/** 14.3 — one sweep plan, with the existing corpus when the caller has one. */
function planBody(
  feed: string,
  source?: string,
  existing?: unknown[],
  maxAgeDays?: number,
  staleSeenDays?: number
): {
  feed: string;
  source?: string;
  existing?: unknown[];
  maxAgeDays?: number;
  staleSeenDays?: number;
} {
  return { feed, source, existing, maxAgeDays, staleSeenDays };
}

/** 14.2 — parse an RSS/Atom feed or a board-API payload into raw postings. */
export function useParseFeed() {
  return useMutation({
    mutationFn: async (input: { feed: string; source?: string }) =>
      (await api.create<unknown>(endpoints.jobIngestParse, parseBody(input.feed, input.source))) as ParsedFeed,
    onError: fail("Couldn't parse that feed."),
  });
}

/** 14.3 — collapse exact-fingerprint duplicates to one survivor. */
export function useDedupeJobs() {
  return useMutation({
    mutationFn: async (postings: unknown[]) =>
      (await api.create<unknown>(endpoints.jobIngestDedupe, dedupeBody(postings))) as PostingCollection,
    onError: fail("Couldn't de-duplicate those postings."),
  });
}

/** 14.3 — partition postings into fresh / stale / expired / undated. */
export function useFreshnessSweep() {
  return useMutation({
    mutationFn: async (input: {
      postings: unknown[];
      maxAgeDays?: number;
      staleSeenDays?: number;
    }) =>
      (await api.create<unknown>(
        endpoints.jobIngestFreshness,
        sweepBody(input.postings, input.maxAgeDays, input.staleSeenDays)
      )) as FreshnessSweep,
    onError: fail("Couldn't sweep that corpus."),
  });
}

/** 14.3 — one plan for a sweep: create / update / close + within-batch duplicates. */
export function useIngestPlan() {
  return useMutation({
    mutationFn: async (input: {
      feed: string;
      source?: string;
      existing?: unknown[];
      maxAgeDays?: number;
      staleSeenDays?: number;
    }) =>
      (await api.create<unknown>(
        endpoints.jobIngestPlan,
        planBody(input.feed, input.source, input.existing, input.maxAgeDays, input.staleSeenDays)
      )) as IngestPlan,
    onError: fail("Couldn't build the ingestion plan."),
  });
}

/* ------------------------------------------------------------------ */
/* Scheduled ingestion (19.2)                                          */
/* ------------------------------------------------------------------ */

/** A feed's three fields, built in one place so the wire shape is written down once. */
function feedBody(
  name: string,
  url: string,
  source?: string
): { name: string; url: string; source?: string } {
  return { name, url, source };
}

/** 19.2 — subscribe to a feed the nightly sweep will fetch. */
export function useCreateIngestionFeed() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: { name: string; url: string; source?: string }) =>
      api.create<unknown>(
        endpoints.ingestionFeeds,
        feedBody(input.name, input.url, input.source)
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["ingestion", "feeds"] });
      toast.success(translate("ingestion.feedAdded"));
    },
    onError: fail(translate("ingestion.feedAddFailed") ?? "Couldn't add that feed."),
  });
}

/** 19.2 — the one switch: whether the sweep includes this feed. */
export function useToggleIngestionFeed() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: { id: string; enabled: boolean }) =>
      api.update<unknown>(endpoints.ingestionFeed(input.id), { enabled: input.enabled }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["ingestion", "feeds"] });
    },
    onError: fail(translate("ingestion.feedUpdateFailed") ?? "Couldn't update that feed."),
  });
}

/** 19.2 — forget a feed and the runs it filed. */
export function useDeleteIngestionFeed() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.remove(endpoints.ingestionFeed(id)),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["ingestion", "feeds"] });
      qc.invalidateQueries({ queryKey: ["ingestion", "runs"] });
      toast.success(translate("ingestion.feedRemoved"));
    },
    onError: fail(translate("ingestion.feedRemoveFailed") ?? "Couldn't remove that feed."),
  });
}

/**
 * 19.2 — pull one feed now. The answer is the run itself, and a failed pull is
 * still a record: the toast names the sentence the server wrote down.
 */
export function useRunIngestionFeed() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string): Promise<IngestionRunDetail> =>
      normalizeIngestionRunDetail(
        await api.request<unknown>(endpoints.ingestionFeedRun(id), { method: "POST" })
      ),
    onSuccess: (detail) => {
      qc.invalidateQueries({ queryKey: ["ingestion", "feeds"] });
      qc.invalidateQueries({ queryKey: ["ingestion", "runs"] });
      qc.invalidateQueries({ queryKey: ["ingestion", "run", detail.run.id] });
      if (detail.run.status === "failed") {
        toast.error(translate("ingestion.runFailedToast", { reason: detail.run.error ?? "" }));
      } else {
        toast.success(translate("ingestion.runRecordedToast"));
      }
    },
    onError: fail(translate("ingestion.runNowFailed") ?? "Couldn't pull that feed."),
  });
}
