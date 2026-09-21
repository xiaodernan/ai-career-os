"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import type {
  ActivityEvent,
  Application,
  Company,
  Conversation,
  DashboardMetrics,
  InterviewSession,
  Job,
  KnowledgeSource,
  Resume,
  SearchResults,
} from "@/lib/api/types";

/**
 * Resource hooks for the (app) surfaces. Every hook targets the real
 * backend path; while an endpoint is unimplemented it errors with 404 and
 * callers render an EmptyState — the UI never shows fake data.
 */

export function useDashboard() {
  return useQuery({
    queryKey: ["dashboard"],
    queryFn: () => api.get<DashboardMetrics>(endpoints.dashboard),
  });
}

export function useResumes() {
  return useQuery({
    queryKey: ["resumes"],
    queryFn: () => api.list<Resume>(endpoints.resumes, { size: 20 }),
  });
}

export function useJobs(params?: { page?: number; size?: number; q?: string }) {
  return useQuery({
    queryKey: ["jobs", params],
    queryFn: () => api.list<Job>(endpoints.jobs, { size: 20, ...params }),
  });
}

export function useApplications(params?: { page?: number; size?: number }) {
  return useQuery({
    queryKey: ["applications", params],
    queryFn: () => api.list<Application>(endpoints.applications, { size: 10, ...params }),
  });
}

export function useKnowledgeSources() {
  return useQuery({
    queryKey: ["knowledge", "sources"],
    queryFn: () => api.list<KnowledgeSource>(endpoints.knowledge, { size: 20 }),
  });
}

export function useInterviewSessions() {
  return useQuery({
    queryKey: ["interview", "sessions"],
    queryFn: () => api.list<InterviewSession>(endpoints.interviews, { size: 20 }),
  });
}

export function useConversations() {
  return useQuery({
    queryKey: ["conversations"],
    queryFn: () => api.list<Conversation>(endpoints.conversations, { size: 20 }),
  });
}

export function useCompanies(params?: { page?: number; size?: number; q?: string }) {
  return useQuery({
    queryKey: ["companies", params],
    queryFn: () => api.list<Company>(endpoints.companies, { size: 20, ...params }),
  });
}

export function useActivity() {
  return useQuery({
    queryKey: ["activity"],
    queryFn: () => api.list<ActivityEvent>(endpoints.activity, { size: 10 }),
  });
}

export function useGlobalSearch(query: string) {
  return useQuery({
    queryKey: ["search", query],
    queryFn: () => api.get<SearchResults>(endpoints.search, { q: query }),
    enabled: query.trim().length >= 2,
    staleTime: 15_000,
  });
}
