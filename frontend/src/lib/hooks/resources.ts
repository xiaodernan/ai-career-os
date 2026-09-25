"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import {
  list as listOf,
  normalizeApplication,
  normalizeDashboard,
  normalizeJob,
  normalizeMatch,
  normalizeMessages,
  normalizePage,
  normalizePipeline,
  normalizeQuestion,
  normalizeResumeScore,
  normalizeRun,
  normalizeSearch,
  pct,
  serializeJobFilters,
  pick,
  rec,
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

/** GET /resume-versions?resumeId= returns a bare List<ResumeVersionItem{id,resumeId,label,kind,jobId,createdAt}>. */
export function mapResumeVersions(raw: unknown): ResumeVersion[] {
  return listOf(raw, "versions", "resumeVersions", "resume_versions").map((v, i) => ({
    id: idStr(v, `v-${i}`),
    resumeId: str(v, "resumeId", "resume_id"),
    label: str(v, "label", "name", "title"),
    versionNo: num(v, "versionNo", "version_no", "number", "index"),
    isCurrent: Boolean(pick(v, "isCurrent", "is_current", "current")),
    // The backend column is `kind` ("original" | "tailored"); `source` is only a legacy alias.
    source: str(v, "kind", "source", "origin"),
    createdAt: str(v, "createdAt", "created_at"),
    score: normalizeResumeScore(v),
    structured: (pick(v, "structured", "structuredResume", "structured_resume") ??
      null) as ResumeVersion["structured"],
    // The tailored change list; the panel renders it through normalizeTailorDiff.
    diff: pick(v, "diff", "tailorDiff", "tailor_diff") ?? undefined,
  }));
}

export async function fetchResumeVersions(resumeId: string): Promise<ResumeVersion[]> {
  return mapResumeVersions(await api.get<unknown>(endpoints.resumeVersions, { resumeId }));
}

/**
 * Versions live on their own route: the resume detail DTO has no versions array, so reading
 * them off `useResume` yielded [] forever. The query key is prefixed by ["resume", id] so the
 * existing invalidateQueries(["resume", resumeId]) after a parse or a "set current" refreshes it.
 */
export function useResumeVersions(resumeId: string | null) {
  return useQuery({
    queryKey: ["resume", resumeId, "versions"],
    enabled: Boolean(resumeId),
    queryFn: () => fetchResumeVersions(resumeId!),
  });
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
      const clean = serializeJobFilters(params ?? {});
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
      // GET /jobs/saved binds no parameters and answers with the whole bookmark list, so a page
      // size here would be a number the server never reads.
      normalizePage(await api.get<unknown>(endpoints.savedJobs), (j) => ({
        ...normalizeJob(j),
        saved: true,
      })),
  });
}

/* ------------------------------- applications ------------------------------ */

export function useApplications(params?: { page?: number; size?: number; status?: string }) {
  return useQuery({
    queryKey: ["applications", params],
    queryFn: async (): Promise<Page<Application>> =>
      normalizePage(
        await api.get<unknown>(endpoints.applications, { size: 50, ...(params ?? {}) }),
        normalizeApplication
      ),
  });
}

export function useApplicationEvents(id: string | null) {
  return useQuery({
    queryKey: ["application", id, "events"],
    enabled: Boolean(id),
    queryFn: async (): Promise<ApplicationEvent[]> => {
      const raw = await api.get<unknown>(endpoints.applicationTimeline(id!));
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

/** SessionItem scalars, shared by the list row and the {session,…} detail envelope. */
function mapSessionScalars(s: unknown) {
  return {
    id: idStr(s),
    jobId: str(s, "jobId", "job_id") ?? null,
    // InterviewDtos.SessionItem calls the role `positionTitle`; jobTitle/position were
    // never on the wire, so the list row, the session header and the report all lost it.
    jobTitle:
      str(s, "positionTitle", "position_title", "jobTitle", "job_title", "position") ?? null,
    companyName: str(s, "companyName", "company_name") ?? null,
    mode: str(s, "mode", "type", "kind") ?? "mixed",
    status: str(s, "status") ?? "active",
    difficulty: num(s, "difficulty", "depth", "level"),
    startedAt: str(s, "startedAt", "started_at", "createdAt", "created_at"),
    finishedAt: str(s, "finishedAt", "finished_at") ?? null,
  };
}

export function mapInterviewSessionItem(s: unknown): InterviewSession {
  return {
    ...mapSessionScalars(s),
    questionCount: num(s, "questionCount", "question_count", "turnCount"),
    // the server stores the report's 0..1 fraction; every score on screen is a percentage
    overall: pct(num(s, "overall", "score", "overallScore")),
  };
}

/** SessionDetail is {session, turns, evaluation} — turns/evaluation are SIBLINGS of session. */
export function mapInterviewSessionDetail(raw: unknown, fallbackId?: string | null) {
  const sess = pick(raw, "session") ?? raw;
  const turns = listOf(raw, "turns", "history", "answers", "questions");
  const lastAssistant = [...turns].reverse().find((t) => str(t, "role") === "assistant");
  const cqMeta = rec(pick(lastAssistant, "questionMeta", "question_meta")) ?? {};
  return {
    ...mapSessionScalars(sess),
    id: idStr(sess, fallbackId ?? ""),
    questionCount: num(sess, "questionCount", "question_count") || turns.length,
    currentQuestion: normalizeQuestion(
      pick(raw, "currentQuestion", "current_question") ??
        pick(sess, "currentQuestion", "current_question", "next") ??
        (lastAssistant ? { ...cqMeta, text: str(lastAssistant, "content") } : null)
    ),
    history: turns,
    report: pick(raw, "evaluation", "report") ?? pick(sess, "evaluation", "report") ?? null,
  };
}

export function useInterviewSessions() {
  return useQuery({
    queryKey: ["interview", "sessions"],
    queryFn: async (): Promise<Page<InterviewSession>> =>
      normalizePage(await api.get<unknown>(endpoints.interviews, { size: 50 }), (s) =>
        mapInterviewSessionItem(s)
      ),
  });
}

export function useInterviewSession(id: string | null) {
  return useQuery({
    queryKey: ["interview", "session", id],
    enabled: Boolean(id),
    queryFn: async () =>
      mapInterviewSessionDetail(await api.get<unknown>(endpoints.interview(id!)), id)
  });
}

/* -------------------------------- activity --------------------------------- */

/** GET /activity/runs pages by "recent": it binds `limit`, and has no page index to send. */
export function useActivityRuns(params?: { limit?: number }) {
  return useQuery({
    queryKey: ["activity", "runs", params],
    queryFn: async (): Promise<Page<ActivityRun>> =>
      // An absent `limit` is left out of the URL rather than guessed at here, so the caller that
      // wants the whole debug feed gets the window the handler itself defaults to.
      normalizePage(
        await api.get<unknown>(endpoints.activityRuns, { limit: params?.limit }),
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
      return normalizeSearch(raw);
    },
    enabled: query.trim().length >= 2,
    staleTime: 15_000,
  });
}
