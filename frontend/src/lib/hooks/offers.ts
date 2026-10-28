"use client";

import { useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import { fail } from "@/lib/hooks/failure";
import type {
  CounterOfferDraft,
  NegotiationPlan,
  OfferComparison,
  SalaryBenchmark,
} from "@/lib/api/types";

/**
 * Salary & offer intelligence (Epics 12.1-12.5).
 *
 * Every answer is a deterministic read of the seeded corpus against the
 * caller's own offer — no model invents a number here.
 *
 * The bodies are built by named helpers so the wire shape is written down in
 * one place per route instead of being spread across the call sites.
 */

/** 12.1 — the role to benchmark, with the optional specializations. */
function salaryBody(input: {
  role: string;
  location?: string;
  seniority?: string;
  targetSalary?: number;
  currency?: string;
}): { role: string; location?: string; seniority?: string; targetSalary?: number; currency?: string } {
  return {
    role: input.role,
    location: input.location,
    seniority: input.seniority,
    targetSalary: input.targetSalary,
    currency: input.currency,
  };
}

/** 12.2 — the offer on the table, against the benchmark. */
function negotiateBody(input: {
  role: string;
  location?: string;
  seniority?: string;
  currency?: string;
  offerBase: number;
  matchScore?: number;
}): {
  role: string;
  location?: string;
  seniority?: string;
  currency?: string;
  offerBase: number;
  matchScore?: number;
} {
  return {
    role: input.role,
    location: input.location,
    seniority: input.seniority,
    currency: input.currency,
    offerBase: input.offerBase,
    matchScore: input.matchScore,
  };
}

/** One equity grant, in the engine's own field names. */
function equityBody(equity: {
  shares: number;
  strikePrice: number;
  currentPrice: number;
  vestYears?: number;
}): { shares: number; strikePrice: number; currentPrice: number; vestYears?: number } {
  return {
    shares: equity.shares,
    strikePrice: equity.strikePrice,
    currentPrice: equity.currentPrice,
    vestYears: equity.vestYears,
  };
}

/** 12.3 / 12.5 — one offer, with its grant. */
function offerBody(offer: {
  label: string;
  base: number;
  bonus: number;
  equity?: { shares: number; strikePrice: number; currentPrice: number; vestYears?: number };
}): { label: string; base: number; bonus: number; equity?: unknown } {
  return {
    label: offer.label,
    base: offer.base,
    bonus: offer.bonus,
    equity: offer.equity ? equityBody(offer.equity) : undefined,
  };
}

/** 12.3 / 12.5 — the offers to compare. */
function compareBody(input: {
  role: string;
  location?: string;
  seniority?: string;
  currency?: string;
  matchScore?: number;
  offers: Array<{
    label: string;
    base: number;
    bonus: number;
    equity?: { shares: number; strikePrice: number; currentPrice: number; vestYears?: number };
  }>;
}): {
  role: string;
  location?: string;
  seniority?: string;
  currency?: string;
  matchScore?: number;
  offers: unknown[];
} {
  return {
    role: input.role,
    location: input.location,
    seniority: input.seniority,
    currency: input.currency,
    matchScore: input.matchScore,
    offers: input.offers.map(offerBody),
  };
}

/** 12.4 — the counter-offer request. */
function counterBody(input: {
  role: string;
  location?: string;
  seniority?: string;
  currency?: string;
  offerBase: number;
  matchScore?: number;
}): {
  role: string;
  location?: string;
  seniority?: string;
  currency?: string;
  offerBase: number;
  matchScore?: number;
} {
  return {
    role: input.role,
    location: input.location,
    seniority: input.seniority,
    currency: input.currency,
    offerBase: input.offerBase,
    matchScore: input.matchScore,
  };
}

/** 12.1 — salary percentiles for a role. */
export function useSalaryBenchmark() {
  return useMutation({
    mutationFn: async (input: {
      role: string;
      location?: string;
      seniority?: string;
      targetSalary?: number;
      currency?: string;
    }) =>
      (await api.create<unknown>(endpoints.offerSalaryBenchmark, salaryBody(input))) as SalaryBenchmark,
    onError: fail("failures.offerBenchmark"),
  });
}

/** 12.2 — the negotiation coach. */
export function useNegotiate() {
  return useMutation({
    mutationFn: async (input: {
      role: string;
      location?: string;
      seniority?: string;
      currency?: string;
      offerBase: number;
      matchScore?: number;
    }) => (await api.create<unknown>(endpoints.offerNegotiate, negotiateBody(input))) as NegotiationPlan,
    onError: fail("failures.negotiationPlan"),
  });
}

/** 12.3 / 12.5 — compare several offers by total compensation. */
export function useCompareOffers() {
  return useMutation({
    mutationFn: async (input: {
      role: string;
      location?: string;
      seniority?: string;
      currency?: string;
      matchScore?: number;
      offers: Array<{
        label: string;
        base: number;
        bonus: number;
        equity?: { shares: number; strikePrice: number; currentPrice: number; vestYears?: number };
      }>;
    }) => (await api.create<unknown>(endpoints.offerCompare, compareBody(input))) as OfferComparison,
    onError: fail("failures.offerCompare"),
  });
}

/** 12.4 — the counter-offer draft. */
export function useCounterOffer() {
  return useMutation({
    mutationFn: async (input: {
      role: string;
      location?: string;
      seniority?: string;
      currency?: string;
      offerBase: number;
      matchScore?: number;
    }) => (await api.create<unknown>(endpoints.offerCounterOffer, counterBody(input))) as CounterOfferDraft,
    onError: fail("failures.counterOffer"),
  });
}
