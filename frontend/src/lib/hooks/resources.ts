"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import {
  list as listOf,
  normalizeApplication,
  normalizeApplicationEvent,
  normalizeDashboard,
  normalizeIngestionFeed,
  normalizeIngestionRun,
  normalizeIngestionRunDetail,
  normalizeJob,
  normalizeMatch,
  normalizeMemory,
  normalizeMessages,
  normalizePage,
  normalizePipeline,
  normalizeQuestion,
  normalizeResumeScore,
  normalizeRun,
  normalizeSavedSearch,
  normalizeSearch,
  pct,
  serializeJobFilters,
  pick,
  str,
  num,
} from "@/lib/api/normalize";
import type {
  ActivityRun,
  Application,
  ApplicationEvent,
  Company,
  Contact,
  CompanyDetail,
  CompanySource,
  Conversation,
  InterviewSession,
  IngestionFeed,
  IngestionRun,
  IngestionRunDetail,
  Job,
  KnowledgeNote,
  KnowledgeSource,
  MemoryItem,
  Page,
  Resume,
  ResumeScore,
  ResumeVersion,
  SavedSearch,
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

export function useResumes(params?: { page?: number; size?: number }) {
  return useQuery({
    queryKey: ["resumes", params],
    queryFn: async (): Promise<Page<Resume>> =>
      normalizePage(
        await api.get<unknown>(endpoints.resumes, { size: 20, ...(params ?? {}) }),
        mapResume
      ),
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
        // The name ResumeDetail authors. The two names asked here before were answered by
        // nothing — the wire has always carried the key, not a name or a URL.
        sourceFileKey: str(body, "sourceFileKey") ?? null,
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
  /** `ORDERINGS` key; absent/empty lets the server pick (relevance for `q`, recency for a browse). */
  sort?: string;
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
      // size here would be a number the server never reads. Each row is a SavedJobItem: the spread
      // hands `job` to `normalizeJob`, which stops at the unwrap, so the two names the wrapper
      // itself owns -- the note written at save time and when that was -- are read here.
      normalizePage(await api.get<unknown>(endpoints.savedJobs), (j) => ({
        ...normalizeJob(j),
        saved: true,
        note: str(j, "note"),
        savedAt: str(j, "savedAt"),
      })),
  });
}

/** The caller's saved searches, newest first (roadmap 19.1). */
export function useSavedSearches() {
  return useQuery({
    queryKey: ["saved-searches"],
    queryFn: async (): Promise<SavedSearch[]> =>
      listOf<unknown>(await api.get<unknown>(endpoints.savedSearches)).map(normalizeSavedSearch),
  });
}

/* ---------------------------- scheduled ingestion -------------------------- */

/** The caller's subscribed feeds, newest first, each with its last run (roadmap 19.2). */
export function useIngestionFeeds() {
  return useQuery({
    queryKey: ["ingestion", "feeds"],
    queryFn: async (): Promise<IngestionFeed[]> =>
      listOf<unknown>(await api.get<unknown>(endpoints.ingestionFeeds)).map(normalizeIngestionFeed),
  });
}

/** What the sweep did with those feeds, newest first. */
export function useIngestionRuns(limit = 20) {
  return useQuery({
    queryKey: ["ingestion", "runs", limit],
    queryFn: async (): Promise<IngestionRun[]> =>
      listOf<unknown>(await api.get<unknown>(endpoints.ingestionRuns, { limit })).map(
        normalizeIngestionRun
      ),
  });
}

/** One run's stored plan — fetched only when the reader opens the row. */
export function useIngestionRunDetail(id: string | null) {
  return useQuery({
    queryKey: ["ingestion", "run", id],
    enabled: id !== null,
    queryFn: async (): Promise<IngestionRunDetail> =>
      normalizeIngestionRunDetail(await api.get<unknown>(endpoints.ingestionRun(id ?? ""))),
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

/**
 * One application by id. The board's deep link carries only the id, and the row it names can sit
 * on a page the board has not fetched -- the attention rows are the oldest ones and sort last --
 * so it is fetched directly rather than searched for page by page. `enabled` keeps a null id
 * from ever spending `/applications/null`.
 */
export function useApplication(id: string | null) {
  return useQuery({
    queryKey: ["application", id],
    enabled: Boolean(id),
    queryFn: async (): Promise<Application> =>
      normalizeApplication(await api.get<unknown>(endpoints.application(id!))),
  });
}

export function useApplicationEvents(id: string | null) {
  return useQuery({
    queryKey: ["application", id, "events"],
    enabled: Boolean(id),
    queryFn: async (): Promise<ApplicationEvent[]> => {
      const raw = await api.get<unknown>(endpoints.applicationTimeline(id!));
      // The mapping is a wire reader, so it lives with the others in normalize.ts where it can
      // be tested; it used to be inline here, unread and untested, which is how the nested
      // `payload` stayed invisible.
      return listOf(raw, "items", "events", "content").map(normalizeApplicationEvent);
    },
  });
}

/* -------------------------------- companies -------------------------------- */

/** Accepts either a plain string or an array of strings for a text field. */
function strList(raw: unknown, ...keys: string[]): string[] | undefined {
  const out = listOf<string>(raw, ...keys).map(String);
  return out.length ? out : undefined;
}

/**
 * One company row. Every name here is a component of `JobDtos.CompanyItem` and nothing else: the
 * mapper used to probe `title`, `url`, `logo`, `sector`, `employees`, `headcount`, `summary`,
 * `description`, `technologies`, `stack`, `values`, `process`, `jobCount` and a `location` no column
 * backs — fourteen aliases, none of which any producer writes, each one a shape this silently
 * reinterpreted. It also read the count out of `openRoles` and the roles out of the same key, which
 * is why the company page could never list a role.
 */
function mapCompany(raw: unknown, fallbackId = ""): Company {
  return {
    id: idStr(raw, fallbackId),
    name: str(raw, "name") ?? "Unknown",
    website: str(raw, "website") ?? null,
    logoUrl: str(raw, "logoUrl") ?? null,
    industry: str(raw, "industry") ?? null,
    size: str(raw, "size") ?? null,
    overview: str(raw, "overview") ?? null,
    techStack: strList(raw, "techStack") ?? [],
    culture: str(raw, "culture") ?? null,
    interviewProcess: str(raw, "interviewProcess") ?? null,
    sources: listOf(raw, "sources").map(mapCompanySource).filter((s) => s.type || s.title || s.note || s.url),
    openRoleCount: num(raw, "openRoleCount"),
  };
}

/** `{type, title?, note?, url?}` — the shape both writers of `companies.sources` fill. */
function mapCompanySource(raw: unknown): CompanySource {
  return {
    type: str(raw, "type") ?? undefined,
    title: str(raw, "title") ?? undefined,
    note: str(raw, "note") ?? undefined,
    url: str(raw, "url") ?? undefined,
  };
}

export function useCompanies(params?: { page?: number; size?: number; q?: string }) {
  return useQuery({
    queryKey: ["companies", params],
    queryFn: async (): Promise<Page<Company>> =>
      // The list rows carry their own id, so no fallback is passed: `normalizePage`'s mapper takes an
      // index second, and a name that read one would be a silent id of "0".
      normalizePage(await api.get<unknown>(endpoints.companies, { size: 20, ...(params ?? {}) }),
        (row) => mapCompany(row)),
  });
}

/**
 * `GET /companies/{id}` answers `CompanyDetail` — `{company, openRoles}` — so the roles are read off
 * the envelope, not off the company: the hook used to look for `openRoles` inside the profile it had
 * just picked out, where the only thing that ever matched was the count.
 */
/**
 * The registry list, most recently updated first — the order the backend orders by, so
 * the page's ordering is a pass-through rather than a second opinion. The route answers
 * a bare list (every row is this user's; there is nothing to page), which the hook wraps
 * in the page envelope `ModuleView` renders, with total = items.
 */
export function useContacts() {
  return useQuery({
    queryKey: ["contacts"],
    queryFn: async (): Promise<Page<Contact>> => {
      const items = listOf(await api.get<unknown>(endpoints.contacts), "items").map(mapContact);
      return { items, total: items.length, page: 0, size: items.length };
    },
  });
}

/** One registry row, read under the names `ContactDtos.ContactItem` spells. */
function mapContact(raw: unknown): Contact {
  return {
    id: idStr(raw),
    name: str(raw, "name") ?? "Unknown",
    role: str(raw, "role"),
    company: str(raw, "company"),
    relation: str(raw, "relation"),
    email: str(raw, "email"),
    notes: str(raw, "notes"),
    lastTouchAt: str(raw, "lastTouchAt"),
    createdAt: str(raw, "createdAt"),
    updatedAt: str(raw, "updatedAt"),
  };
}

export function useCompany(id: string | null) {
  return useQuery({
    queryKey: ["company", id],
    enabled: Boolean(id),
    queryFn: async (): Promise<CompanyDetail> => {
      const raw = await api.get<{ company?: unknown; openRoles?: unknown }>(
        endpoints.company(id!)
      );
      return {
        company: mapCompany(raw.company, id!),
        openRoles: listOf(raw, "openRoles").map(normalizeJob),
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

/**
 * The knowledge list. `documentId` narrows it server-side, which is what makes `/knowledge?src=` a
 * link rather than a hint: the page holds one page of sources, so filtering what arrived locally could
 * not tell a deleted document from one that simply sits further down the list.
 */
export function useKnowledgeSources(live = false, documentId?: string,
                               params?: { page?: number; size?: number }) {
  return useQuery({
    queryKey: ["knowledge", "sources", live ? "live" : "once", documentId ?? null, params],
    queryFn: async (): Promise<Page<KnowledgeSource>> =>
      normalizePage(
        await api.get<unknown>(endpoints.knowledge,
                               { size: 20, documentId, ...(params ?? {}) }),
        mapSource
      ),
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

export function useKnowledgeNotes(params?: { page?: number; size?: number }) {
  return useQuery({
    queryKey: ["knowledge", "notes", params],
    queryFn: async (): Promise<Page<KnowledgeNote>> =>
      normalizePage(
        await api.get<unknown>(endpoints.knowledgeNotes, { size: 20, ...(params ?? {}) }),
        (n) => ({
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
  // The pending question is the last *interviewer* turn: those are the only two roles the backend
  // writes ("interviewer" / "candidate" -- `assistant` belongs to the copilot's chat table, not
  // here), so a search for an assistant row matched nothing on every payload, left
  // `currentQuestion` null, and the runner page re-fired the opening POST -- which answers 400
  // "Session already has turns". Reloading mid-interview therefore lost the question.
  const lastQuestion = [...turns].reverse().find((t) => str(t, "role") === "interviewer");
  return {
    ...mapSessionScalars(sess),
    id: idStr(sess, fallbackId ?? ""),
    questionCount: num(sess, "questionCount", "question_count") || turns.length,
    currentQuestion: normalizeQuestion(lastQuestion),
    history: turns,
    report: pick(raw, "evaluation", "report") ?? pick(sess, "evaluation", "report") ?? null,
  };
}

export function useInterviewSessions(params?: { page?: number; size?: number }) {
  return useQuery({
    queryKey: ["interview", "sessions", params],
    queryFn: async (): Promise<Page<InterviewSession>> =>
      normalizePage(
        await api.get<unknown>(endpoints.interviews, { size: 20, ...(params ?? {}) }),
        (s) => mapInterviewSessionItem(s)
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
export function useActivityRuns(params?: { page?: number; size?: number }) {
  return useQuery({
    queryKey: ["activity", "runs", params],
    queryFn: async (): Promise<Page<ActivityRun>> =>
      normalizePage(
        await api.get<unknown>(endpoints.activityRuns, { size: 30, ...(params ?? {}) }),
        (r) => normalizeRun(r)
      ),
  });
}

/* ------------------------------ conversations ------------------------------ */

export function useConversations(params?: { page?: number; size?: number }) {
  return useQuery({
    queryKey: ["conversations", params],
    queryFn: async (): Promise<Page<Conversation>> =>
      normalizePage(
        await api.get<unknown>(endpoints.conversations, { size: 20, ...(params ?? {}) }),
        (c) => ({
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
      // The summary writes eight keys; this hook asks the three the spend card shows, in the
      // handler's own spellings. The rest are declared unread by the anonymous-mappers gate.
      return {
        requests: num(raw, "requests"),
        totalTokens: num(raw, "totalTokens"),
        costUsd: num(raw, "costUsd"),
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

/**
 * Reads the caller's memories, newest update first.
 *
 * The `kinds` filter is passed through as one comma-joined value, which is the spelling
 * the handler binds (`List<String> kinds`). An empty list is no filter rather than a filter
 * for nothing: an absent parameter is what "every kind" looks like on the wire, because
 * `kinds=` would bind a list holding one empty string and match no row at all.
 */
export async function fetchMemories(kinds?: string[]): Promise<MemoryItem[]> {
  const kindsParam = kinds?.length ? kinds.join(",") : undefined;
  const raw = await api.get<unknown>(endpoints.memories, { kinds: kindsParam });
  return mapMemories(raw);
}

/** A bare array (the backend controller's own shape) or the ai-service's `{items}`. */
export function mapMemories(raw: unknown): MemoryItem[] {
  return listOf(raw, "items").map(normalizeMemory);
}

/**
 * Every memory the agents hold about the caller (AGENTS.md §6).
 *
 * A list, not a page: the point is to read what the model believes and correct it, and a
 * windowed view would hide the sentence a user came to find. `kinds` is passed through
 * verbatim, so the caller narrows without the client reimplementing the filter.
 */
export function useMemories(kinds?: string[]) {
  return useQuery({
    queryKey: ["memories", kinds ?? []],
    queryFn: () => fetchMemories(kinds),
  });
}
