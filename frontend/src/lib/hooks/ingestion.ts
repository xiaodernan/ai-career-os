"use client";

import { useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import { fail } from "@/lib/hooks/failure";
import type {
  IngestPlan,
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
