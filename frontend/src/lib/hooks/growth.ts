"use client";

import { useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import { fail } from "@/lib/hooks/failure";
import type {
  CompanyBrief,
  GapReport,
  InterviewPrep,
  LearningPlan,
  LearningPriority,
  OutreachDraft,
  ProgressionPlan,
  ReadinessVerdict,
  RoleSuggestions,
  SkillDemand,
  SkillProgress,
  StoryBank,
} from "@/lib/api/types";

/**
 * The granular growth engines (Epics 10.1-10.13), each asked on its own.
 *
 * The `/growth` page reads the 10.2 aggregate in one call; these hooks are the
 * same engines one at a time, so a panel that only wants the learning
 * priority does not have to run the whole report to get it.
 *
 * The bodies are built by named helpers so the wire shape is written down in
 * one place per route instead of being spread across the call sites.
 */

/** The role-anchored engines' request: the role, the version, and the specializations. */
function roleBody(input: {
  targetRole: string;
  seniority?: string;
  resumeVersionId?: string;
  location?: string;
  currency?: string;
  targetSalary?: number;
  top?: number;
}): {
  targetRole: string;
  seniority?: string;
  resumeVersionId?: string;
  location?: string;
  currency?: string;
  targetSalary?: number;
  top?: number;
} {
  return {
    targetRole: input.targetRole,
    seniority: input.seniority,
    resumeVersionId: input.resumeVersionId,
    location: input.location,
    currency: input.currency,
    targetSalary: input.targetSalary,
    top: input.top,
  };
}

/** The profile-anchored engines' request: the version and how many rows. */
function profileBody(input: { resumeVersionId?: string; top?: number }): {
  resumeVersionId?: string;
  top?: number;
} {
  return { resumeVersionId: input.resumeVersionId, top: input.top };
}

/** 10.1 — the distance between the profile and the target role. */
export function useGapAnalysis() {
  return useMutation({
    mutationFn: async (input: Parameters<typeof roleBody>[0]) =>
      (await api.create<unknown>(endpoints.growthGapAnalysis, roleBody(input))) as GapReport,
    onError: fail("failures.gapAnalyze"),
  });
}

/** 10.7 — target-role readiness, as one verdict. */
export function useReadiness() {
  return useMutation({
    mutationFn: async (input: Parameters<typeof roleBody>[0]) =>
      (await api.create<unknown>(endpoints.growthReadiness, roleBody(input))) as ReadinessVerdict,
    onError: fail("failures.roleReadiness"),
  });
}

/** 10.5 — the phased learning plan that closes the gaps. */
export function useLearningPlan() {
  return useMutation({
    mutationFn: async (input: Parameters<typeof roleBody>[0]) =>
      (await api.create<unknown>(endpoints.growthLearningPlan, roleBody(input))) as LearningPlan,
    onError: fail("failures.learningPlan"),
  });
}

/** 10.9 — which skills the market asks for, counted from the corpus. */
export function useSkillDemand() {
  return useMutation({
    mutationFn: async (input: Parameters<typeof roleBody>[0]) =>
      (await api.create<unknown>(endpoints.growthSkillDemand, roleBody(input))) as SkillDemand,
    onError: fail("failures.marketDemand"),
  });
}

/** 10.12 — the gaps ranked by importance and by market pull. */
export function useLearningPriority() {
  return useMutation({
    mutationFn: async (input: Parameters<typeof roleBody>[0]) =>
      (await api.create<unknown>(endpoints.growthLearningPriority, roleBody(input))) as LearningPriority,
    onError: fail("failures.priorityRank"),
  });
}

/** 10.11 — the stepping-stone roles toward a dream role. */
export function useProgression() {
  return useMutation({
    mutationFn: async (input: Parameters<typeof roleBody>[0]) =>
      (await api.create<unknown>(endpoints.growthProgression, roleBody(input))) as ProgressionPlan,
    onError: fail("failures.progressionPlan"),
  });
}

/** 10.13 — the pre-interview checklist. */
export function useInterviewPrep() {
  return useMutation({
    mutationFn: async (input: Parameters<typeof roleBody>[0]) =>
      (await api.create<unknown>(endpoints.growthInterviewPrep, roleBody(input))) as InterviewPrep,
    onError: fail("failures.interviewPrep"),
  });
}

/** 6.5 — the STAR story bank, drawn from the profile's own evidence. */
export function useStoryBank() {
  return useMutation({
    mutationFn: async (input: Parameters<typeof profileBody>[0]) =>
      (await api.create<unknown>(endpoints.growthStoryBank, profileBody(input))) as StoryBank,
    onError: fail("failures.storyBank"),
  });
}

/** 10.10 — the target roles this profile could plausibly aim at. */
export function useRoleSuggestions() {
  return useMutation({
    mutationFn: async (input: Parameters<typeof profileBody>[0]) =>
      (await api.create<unknown>(endpoints.growthRoleSuggestions, profileBody(input))) as RoleSuggestions,
    onError: fail("failures.roleSuggest"),
  });
}

/** 4.8 — what the corpus says about one company. */
export function useCompanyBrief() {
  return useMutation({
    mutationFn: async (input: { company: string; top?: number }) =>
      (await api.create<unknown>(endpoints.companyBrief, {
        company: input.company,
        top: input.top,
      })) as CompanyBrief,
    onError: fail("failures.companyCorpus"),
  });
}

/**
 * 10.6 — skill progress between two snapshots. The engine computes the current
 * gap report and diffs it against the previous one the caller holds.
 */
export function useSkillProgress() {
  return useMutation({
    mutationFn: async (input: {
      targetRole?: string;
      seniority?: string;
      resumeVersionId?: string;
      previous?: unknown;
    }) =>
      (await api.create<unknown>(endpoints.growthProgress, {
        targetRole: input.targetRole,
        seniority: input.seniority,
        resumeVersionId: input.resumeVersionId,
        previous: input.previous,
      })) as SkillProgress,
    onError: fail("failures.skillProgress"),
  });
}

/**
 * 11.2 — the outreach message for a real person. Evidence-bound: the validator
 * strips any skill the profile does not support.
 */
export function useOutreachDraft() {
  return useMutation({
    mutationFn: async (input: {
      name: string;
      role?: string;
      company?: string;
      purpose?: string;
      context?: string;
      resumeVersionId?: string;
    }) =>
      (await api.create<unknown>(endpoints.outreachDraft, {
        name: input.name,
        role: input.role,
        company: input.company,
        purpose: input.purpose,
        context: input.context,
        resumeVersionId: input.resumeVersionId,
      })) as OutreachDraft,
    onError: fail("failures.messageDraft"),
  });
}
