"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import {
  list as listOf,
  normalizeDashboard,
  normalizeJob,
  normalizeMatch,
  normalizeMessages,
  normalizePage,
  normalizePipeline,
  normalizeQuestion,
  normalizeResumeScore,
  normalizeRun,
  normalizeSkillGaps,
  pick,
  str,
  num,
} from "@/lib/api/normalize";
import type {
  ActivityRun,
  Application,
  ApplicationEvent,
  Company,
  Conversation,
  InterviewSession,
  Job,
  KnowledgeNote,
  KnowledgeSource,
  Page,
  Resume,
  ResumeScore,
  ResumeVersion,
  SearchResults,
} from "@/lib/api/types";

/**
 * Query hooks for the (app) surfaces. Every hook targets the real backend
 * path; while an endpoint is unimplemented it errors (404) and callers render
 * an EmptyState/ErrorState — the UI never shows fake data.
 */

const idStr = (raw: unknown, fallback = ""): string => String(pick(raw, "id") ?? fallback);

/* ------------------------------- dashboard -------------------------------- */

export function useDashboard() {
  return useQuery({
    queryKey: ["dashboard"],
    queryFn: async () => normalizeDashboard(await api.get<unknown>(endpoints.reportsDashboard)),
  });
}

/** Pipeline counts derive from the same aggregate; separate key so the kanban
 *  summary can refresh independently after a status move. */
export function useDashboardPipeline() {
  return useQuery({
    queryKey: ["dashboard", "pipeline"],
    queryFn: async () => normalizePipeline(await api.get<unknown>(endpoints.reportsDashboard)),
  });
}

/* --------------------------------- resumes -------------------------------- */

function mapResume(raw: unknown): Resume {
  return {
    id: idStr(raw),
    title: str(raw, "title", "name", "fileName", "file_name") ?? "Untitled resume",
    status: str(raw, "status") ?? "uploaded",
    currentVersionId: str(raw, "currentVersionId", "current_version_id") ?? null,
    createdAt: str(raw, "createdAt", "created_at"),
    updatedAt: str(raw, "updatedAt", "updated_at") ?? null,
  };
}

export function useResumes() {
  return useQuery({
    queryKey: ["resumes"],
    queryFn: async (): Promise<Page<Resume>> =>
      normalizePage(await api.get<unknown>(endpoints.resumes, { size: 20 }), mapResume),
  });
}

export function mapResumeVersions(raw: unknown): ResumeVersion[] {
  return listOf(raw, "versions", "resumeVersions", "resume_versions").map((v, i) => ({
    id: idStr(v, `v-${i}`),
    resumeId: str(v, "resumeId", "resume_id"),
    label: str(v, "label", "name", "title"),
    versionNo: num(v, "versionNo", "version_no", "number", "index"),
    isCurrent: Boolean(pick(v, "isCurrent", "is_current", "current")),
    source: str(v, "source", "origin"),
    createdAt: str(v, "createdAt", "created_at"),
    score: normalizeResumeScore(v),
    structured: (pick(v, "structured", "structuredResume", "structured_resume") ??
      null) as ResumeVersion["structured"],
  }));
}

export function useResume(id: string | null) {
  return useQuery({
    queryKey: ["resume", id],
    enabled: Boolean(id),
    queryFn: async (): Promise<Resume> => {
      const raw = await api.get<unknown>(endpoints.resume(id!));
      const body = pick(raw, "resume", "data") ?? raw;
      return {
        ...mapResume(body),
        fileName: str(body, "fileName", "file_name", "originalName") ?? null,
        fileUrl: str(body, "fileUrl", "file_url", "url") ?? null,
        structured: (pick(body, "structured", "structuredResume", "structured_resume") ??
          null) as Resume["structured"],
        score: normalizeResumeScore(body),
        versions: mapResumeVersions(body),
      };
    },
  });
}

export function useResumeScore(id: string | null) {
  return useQuery({
    queryKey: ["resume", id, "score"],
    enabled: Boolean(id),
    queryFn: async (): Promise<ResumeScore | null> =>
      normalizeResumeScore(await api.get<unknown>(endpoints.resume(id!))),
  });
}

/* ----------------------------------- jobs --------------------------------- */

export interface JobFilters {
  q?: string;
  skills?: string;
  location?: string;
  remote?: boolean;
  company?: string;
  min_salary?: number;
  max_salary?: number;
  page?: number;
  size?: number;
}

export function useJobs(params?: JobFilters) {
  return useQuery({
    queryKey: ["jobs", params],
    queryFn: async (): Promise<Page<Job>> => {
      const clean = Object.fromEntries(
        Object.entries(params ?? {}).filter(([, v]) => v !== "" && v !== undefined)
      );
      return normalizePage(
        await api.get<unknown>(endpoints.jobs, { size: 20, ...clean }),
        (j) => normalizeJob(j)
      );
    },
  });
}

export function useJob(id: string | null) {
  return useQuery({
    queryKey: ["job", id],
    enabled: Boolean(id),
    queryFn: async () => {
      const raw = await api.get<unknown>(endpoints.job(id!));
      const body = pick(raw, "job", "data") ?? raw;
      const job = normalizeJob(body);
      const match = normalizeMatch(pick(body, "match", "latestMatch", "latest_match") ?? raw);
      const jd = pick(body, "jd", "jobDescription", "job_description") ?? null;
      return {
        job: { ...job, saved: job.saved ?? Boolean(pick(body, "saved", "is_saved", "isSaved")) },
        match,
        jd: jd as Record<string, unknown> | null,
        skillGaps: normalizeSkillGaps(body),
        evidence: match?.evidence ?? [],
        interviewTopics: match?.interviewTopics ?? [],
        preparation: match?.preparation ?? [],
        structured: pick(body, "structured", "structuredResume"),
      };
    },
  });
}

export function useSavedJobs() {
  return useQuery({
    queryKey: ["saved-jobs"],
    queryFn: async (): Promise<Page<Job>> =>
      normalizePage(await api.get<unknown>(endpoints.savedJobs, { size: 50 }), (j) => ({
        ...normalizeJob(j),
        saved: true,
      })),
  });
}

/* ------------------------------- applications ------------------------------ */

function mapApplication(raw: unknown): Application {
  return {
    id: idStr(raw),
    jobId: str(raw, "jobId", "job_id") ?? null,
    companyId: str(raw, "companyId", "company_id"),
    company: pick<NonNullable<Application["company"]>>(raw, "company") ?? undefined,
    companyName: str(raw, "companyName", "company_name"),
    title: str(raw, "title", "position", "role") ?? "Untitled",
    status: str(raw, "status") ?? "saved",
    matchScore: num(raw, "matchScore", "match_score") ?? null,
    note: str(raw, "note", "notes") ?? null,
    reminderAt: str(raw, "reminderAt", "reminder_at") ?? null,
    position: num(raw, "position", "orderIndex", "order_index", "sortOrder", "sort_order"),
    createdAt: str(raw, "createdAt", "created_at"),
    updatedAt: str(raw, "updatedAt", "updated_at"),
  };
}

export function useApplications(params?: { page?: number; size?: number; status?: string }) {
  return useQuery({
    queryKey: ["applications", params],
    queryFn: async (): Promise<Page<Application>> =>
      normalizePage(
        await api.get<unknown>(endpoints.applications, { size: 50, ...(params ?? {}) }),
        mapApplication
      ),
  });
}

export function useApplicationEvents(id: string | null) {
  return useQuery({
    queryKey: ["application", id, "events"],
    enabled: Boolean(id),
    queryFn: async (): Promise<ApplicationEvent[]> => {
      const raw = await api.get<unknown>(endpoints.applicationEvents(id!));
      return listOf(raw, "items", "events", "content").map((e, i) => ({
        id: idStr(e, `ev-${i}`),
        applicationId: str(e, "applicationId", "application_id"),
        type: str(e, "type", "kind", "event"),
        status: str(e, "status", "to", "toStatus", "to_status"),
        label: str(e, "label", "title", "summary", "description"),
        note: str(e, "note", "notes", "comment") ?? undefined,
        createdAt: str(e, "createdAt", "created_at", "timestamp"),
      }));
    },
  });
}

/* -------------------------------- companies -------------------------------- */

/** Accepts either a plain string or an array of strings for a text field. */
function strList(raw: unknown, ...keys: string[]): string[] | undefined {
  const out = listOf<string>(raw, ...keys).map(String);
  return out.length ? out : undefined;
}

function mapCompany(raw: unknown): Company {
  return {
    id: idStr(raw),
    name: str(raw, "name", "title") ?? "Unknown",
    website: str(raw, "website", "url") ?? null,
    logoUrl: str(raw, "logoUrl", "logo_url", "logo") ?? null,
    industry: str(raw, "industry", "sector") ?? null,
    size: str(raw, "size", "employees", "headcount") ?? null,
    hq: str(raw, "hq", "headquarters", "location") ?? null,
    overview: str(raw, "overview", "summary", "description") ?? null,
    techStack: strList(raw, "techStack", "tech_stack", "technologies", "stack") ?? [],
    culture: strList(raw, "culture", "values"),
    interviewProcess: strList(raw, "interviewProcess", "interview_process", "process", "interviewSteps", "interview_steps"),
    rolesCount: num(raw, "rolesCount", "roles_count", "openRoles", "jobCount"),
  };
}

export function useCompanies(params?: { page?: number; size?: number; q?: string }) {
  return useQuery({
    queryKey: ["companies", params],
    queryFn: async (): Promise<Page<Company>> =>
      normalizePage(await api.get<unknown>(endpoints.companies, { size: 20, ...(params ?? {}) }), mapCompany),
  });
}

export function useCompany(id: string | null) {
  return useQuery({
    queryKey: ["company", id],
    enabled: Boolean(id),
    queryFn: async () => {
      const raw = await api.get<unknown>(endpoints.company(id!));
      const body = pick(raw, "company", "data") ?? raw;
      return {
        company: { ...mapCompany(body), id: idStr(body, id ?? "") } as Company,
        openRoles: listOf(body, "openRoles", "open_roles", "roles", "jobs", "positions").map(
          normalizeJob
        ),
      };
    },
  });
}

/* -------------------------------- knowledge -------------------------------- */

function mapSource(raw: unknown): KnowledgeSource {
  return {
    id: idStr(raw),
    kind: str(raw, "kind", "type") ?? "document",
    title: str(raw, "title", "name", "fileName", "file_name") ?? "Untitled",
    status: str(raw, "status") ?? "pending",
    error: str(raw, "error", "errorMessage", "error_message") ?? null,
    chunkCount: num(raw, "chunkCount", "chunk_count", "chunks"),
    createdAt: str(raw, "createdAt", "created_at"),
    updatedAt: str(raw, "updatedAt", "updated_at"),
    taskId: str(raw, "taskId", "task_id") ?? null,
    documentId: str(raw, "documentId", "document_id") ?? null,
  };
}

export function useKnowledgeSources(live = false) {
  return useQuery({
    queryKey: ["knowledge", "sources", live ? "live" : "once"],
    queryFn: async (): Promise<Page<KnowledgeSource>> =>
      normalizePage(await api.get<unknown>(endpoints.knowledge, { size: 50 }), mapSource),
    refetchInterval: (q) => {
      if (!live) return false;
      const items = q.state.data?.items ?? [];
      return items.some((s) => s.status === "ingesting" || s.status === "pending") ? 4000 : false;
    },
  });
}

export function useSourceStatus(id: string | null) {
  return useQuery({
    queryKey: ["knowledge", "source", id, "status"],
    enabled: Boolean(id),
    refetchInterval: (q) => {
      const status = str(q.state.data, "status");
      return status === "ready" || status === "failed" ? false : 3500;
    },
    queryFn: async () => {
      const raw = await api.get<unknown>(endpoints.knowledgeSourceStatus(id!));
      return {
        status: str(raw, "status") ?? "pending",
        error: str(raw, "error", "message") ?? null,
        chunks: num(raw, "chunks", "chunkCount", "chunk_count"),
        taskId: str(raw, "taskId", "task_id") ?? null,
      };
    },
  });
}

export function useKnowledgeNotes() {
  return useQuery({
    queryKey: ["knowledge", "notes"],
    queryFn: async (): Promise<Page<KnowledgeNote>> =>
      normalizePage(await api.get<unknown>(endpoints.knowledgeNotes, { size: 50 }), (n) => ({
        id: idStr(n),
        title: str(n, "title", "name") ?? "Untitled note",
        content: str(n, "content", "body", "text") ?? "",
        kind: str(n, "kind", "type"),
        tags: listOf<string>(n, "tags", "labels").map(String),
        sourceId: str(n, "sourceId", "source_id") ?? null,
        createdAt: str(n, "createdAt", "created_at"),
        updatedAt: str(n, "updatedAt", "updated_at"),
      })),
  });
}

/* -------------------------------- interviews ------------------------------- */

export function useInterviewSessions() {
  return useQuery({
    queryKey: ["interview", "sessions"],
    queryFn: async (): Promise<Page<InterviewSession>> =>
      normalizePage(await api.get<unknown>(endpoints.interviews, { size: 50 }), (s) => ({
        id: idStr(s),
        jobId: str(s, "jobId", "job_id") ?? null,
        jobTitle: str(s, "jobTitle", "job_title", "position") ?? null,
        companyName: str(s, "companyName", "company_name") ?? null,
        mode: str(s, "mode", "type", "kind") ?? "mixed",
        status: str(s, "status") ?? "active",
        difficulty: num(s, "difficulty", "depth", "level"),
        questionCount: num(s, "questionCount", "question_count", "turnCount"),
        startedAt: str(s, "startedAt", "started_at", "createdAt", "created_at"),
        finishedAt: str(s, "finishedAt", "finished_at") ?? null,
        overall: num(s, "overall", "score", "overallScore"),
      })),
  });
}

export function useInterviewSession(id: string | null) {
  return useQuery({
    queryKey: ["interview", "session", id],
    enabled: Boolean(id),
    queryFn: async () => {
      const raw = await api.get<unknown>(endpoints.interview(id!));
      const body = pick(raw, "session", "data") ?? raw;
      return {
        id: idStr(body, id ?? ""),
        jobId: str(body, "jobId", "job_id") ?? null,
        jobTitle: str(body, "jobTitle", "job_title") ?? null,
        companyName: str(body, "companyName", "company_name") ?? null,
        mode: str(body, "mode", "type") ?? "mixed",
        status: str(body, "status") ?? "active",
        difficulty: num(body, "difficulty", "depth", "level"),
        questionCount: num(body, "questionCount", "question_count"),
        startedAt: str(body, "startedAt", "started_at"),
        finishedAt: str(body, "finishedAt", "finished_at") ?? null,
        currentQuestion: normalizeQuestion(
          pick(body, "currentQuestion", "current_question", "question", "next") ?? body
        ),
        history: listOf(body, "history", "answers", "turns", "questions"),
        report: pick(body, "report", "evaluation") ?? null,
      };
    },
  });
}

/* -------------------------------- activity --------------------------------- */

export function useActivityRuns(params?: { page?: number; size?: number }) {
  return useQuery({
    queryKey: ["activity", "runs", params],
    queryFn: async (): Promise<Page<ActivityRun>> =>
      normalizePage(
        await api.get<unknown>(endpoints.activityRuns, { size: 20, ...(params ?? {}) }),
        (r) => normalizeRun(r)
      ),
  });
}

export function useActivityRun(id: string | null) {
  return useQuery({
    queryKey: ["activity", "run", id],
    enabled: Boolean(id),
    queryFn: async () => normalizeRun(await api.get<unknown>(endpoints.activityRun(id!))),
  });
}

/* ------------------------------ conversations ------------------------------ */

export function useConversations() {
  return useQuery({
    queryKey: ["conversations"],
    queryFn: async (): Promise<Page<Conversation>> =>
      normalizePage(await api.get<unknown>(endpoints.conversations, { size: 50 }), (c) => ({
        id: idStr(c),
        title: str(c, "title", "name") ?? "Conversation",
        updatedAt: str(c, "updatedAt", "updated_at"),
        createdAt: str(c, "createdAt", "created_at"),
        lastMessagePreview: str(c, "lastMessagePreview", "preview", "lastMessage") ?? undefined,
        messageCount: num(c, "messageCount", "message_count"),
      })),
  });
}

export function useConversationMessages(id: string | null) {
  return useQuery({
    queryKey: ["conversation", id, "messages"],
    enabled: Boolean(id),
    queryFn: async () => normalizeMessages(await api.get<unknown>(endpoints.conversationMessages(id!))),
  });
}

/* ---------------------------------- misc ---------------------------------- */

export function useAIUsage() {
  return useQuery({
    queryKey: ["ai-usage"],
    queryFn: async () => {
      const raw = await api.get<unknown>(endpoints.aiUsage);
      const u = pick(raw, "summary", "data") ?? raw;
      return {
        requests: num(u, "requests", "requestCount", "request_count", "total"),
        tokensTotal: num(u, "tokensTotal", "tokens_total", "tokens"),
        tokensIn: num(u, "tokensIn", "tokens_in", "promptTokens"),
        tokensOut: num(u, "tokensOut", "tokens_out", "completionTokens"),
        costUsd: num(u, "costUsd", "cost_usd", "cost", "totalCost"),
        byAgent: listOf(u, "byAgent", "by_agent").map((a) => ({
          agent: str(a, "agent", "name", "key") ?? "unknown",
          requests: num(a, "requests", "count"),
          tokens: num(a, "tokens", "tokensTotal"),
          costUsd: num(a, "costUsd", "cost"),
        })),
        byModel: listOf(u, "byModel", "by_model").map((m) => ({
          model: str(m, "model", "name", "key") ?? "unknown",
          requests: num(m, "requests", "count"),
          tokens: num(m, "tokens", "tokensTotal"),
          costUsd: num(m, "costUsd", "cost"),
        })),
        daily: listOf(u, "daily", "byDay", "by_day").map((d) => ({
          date: str(d, "date", "day") ?? "",
          requests: num(d, "requests", "count"),
          tokens: num(d, "tokens", "tokensTotal"),
          costUsd: num(d, "costUsd", "cost"),
        })),
        updatedAt: str(u, "updatedAt", "updated_at"),
      };
    },
  });
}

export function useGlobalSearch(query: string) {
  return useQuery({
    queryKey: ["search", query],
    queryFn: async (): Promise<SearchResults> => {
      const raw = await api.get<unknown>(endpoints.search, { q: query });
      const groupsRaw = listOf(raw, "groups");
      if (groupsRaw.length) {
        return {
          groups: groupsRaw.map((g) => ({
            label: str(g, "label", "type", "name") ?? "Results",
            items: listOf(g, "items").map((i) => ({
              id: idStr(i),
              type: str(i, "type", "kind") ?? "result",
              title: str(i, "title", "name") ?? "",
              subtitle: str(i, "subtitle", "description", "snippet") ?? undefined,
              href: str(i, "href", "url", "link") ?? "#",
            })),
          })),
        };
      }
      // flat `{items:[…]}` — group client-side by the real `type` field
      const flat = listOf(raw, "items", "results");
      const byType = new Map<string, unknown[]>();
      for (const i of flat) {
        const t = str(i, "type", "kind") ?? "results";
        byType.set(t, [...(byType.get(t) ?? []), i]);
      }
      return {
        groups: [...byType.entries()].map(([label, items]) => ({
          label: label.charAt(0).toUpperCase() + label.slice(1),
          items: items.map((i) => ({
            id: idStr(i),
            type: label,
            title: str(i, "title", "name") ?? "",
            subtitle: str(i, "subtitle", "description") ?? undefined,
            href: str(i, "href", "url", "link") ?? "#",
          })),
        })),
      };
    },
    enabled: query.trim().length >= 2,
    staleTime: 15_000,
  });
}
