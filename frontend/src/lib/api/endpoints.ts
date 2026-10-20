/**
 * API surface for AI Career OS, derived from docs/architecture.md
 * (§3 module map, §9 conventions). Backend is being built in parallel;
 * when an endpoint 404s the UI must degrade to an EmptyState — never fake data.
 *
 * This file is the single source of truth for paths. Anything that needs an
 * id/param exposes a builder function so no route hand-concatenates strings.
 *
 * Bodies are the other half of the wire contract and they follow one rule: a field goes out
 * under a single name (see lib/api/body.ts). The backend's @JsonAlias accepts either spelling,
 * but not a body carrying both, so a duplicate is a failed request rather than a tolerant one.
 */

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8080/api/v1";

const seg = (v: string | number) => encodeURIComponent(String(v));

export const endpoints = {
  auth: {
    register: "/auth/register",
    login: "/auth/login",
    refresh: "/auth/refresh",
    logout: "/auth/logout",
    forgotPassword: "/auth/password/forgot",
    resetPassword: "/auth/password/reset",
    me: "/users/me",
    profile: "/users/me/profile",
  },

  /* ---------------- Resumes ---------------- */
  resumes: "/resumes",
  resume: (id: string) => `/resumes/${seg(id)}`,
  resumeFile: (id: string) => `/resumes/${seg(id)}/file`,
  resumeUpload: "/resumes/upload",
  resumeParse: (id: string) => `/resumes/${seg(id)}/parse`,
  resumeSetCurrent: (id: string) => `/resumes/${seg(id)}/set-current`,
  resumeVersions: "/resume-versions",
  resumeVersion: (id: string) => `/resume-versions/${seg(id)}`,

  /* ---------------- Jobs / JD / matches ---------------- */
  jobs: "/jobs",
  jobsImport: "/jobs/import",
  job: (id: string) => `/jobs/${seg(id)}`,
  jobSave: (id: string) => `/jobs/${seg(id)}/save`,
  jobMatch: (id: string) => `/jobs/${seg(id)}/match`,
  jobTailor: (id: string) => `/jobs/${seg(id)}/tailor`,
  jobTailoredVersion: (id: string) => `/jobs/${seg(id)}/tailored-version`,
  jobCoverLetter: (id: string) => `/jobs/${seg(id)}/cover-letter`,
  savedJobs: "/jobs/saved",
  jdAnalyze: "/jds",
  jdSuggestions: "/jds/suggestions",

  /* ---------------- Applications ---------------- */
  applications: "/applications",
  application: (id: string) => `/applications/${seg(id)}`,
  applicationReorder: (id: string) => `/applications/${seg(id)}/reorder`,
  applicationTimeline: (id: string) => `/applications/${seg(id)}/timeline`,

  /* ---------------- Companies ---------------- */
  companies: "/companies",
  company: (id: string) => `/companies/${seg(id)}`,

  /* ---------------- Interviews ---------------- */
  interviews: "/interview/sessions",
  interview: (id: string) => `/interview/sessions/${seg(id)}`,
  interviewOpening: (id: string) => `/interview/sessions/${seg(id)}/opening`,
  interviewAnswer: (id: string) => `/interview/sessions/${seg(id)}/answer`,
  interviewFinalize: (id: string) => `/interview/sessions/${seg(id)}/finalize`,

  /* ---------------- Knowledge base (RAG) ---------------- */
  knowledge: "/knowledge/sources",
  knowledgeSource: (id: string) => `/knowledge/sources/${seg(id)}`,
  knowledgeSourceStatus: (id: string) => `/knowledge/sources/${seg(id)}/status`,
  knowledgeNotes: "/knowledge/notes",
  knowledgeNote: (id: string) => `/knowledge/notes/${seg(id)}`,
  knowledgeText: "/knowledge/text",
  knowledgeDocuments: "/knowledge/documents",

  /* ---------------- AI actions (thin proxies over ai-service) ------------ */
  contacts: "/contacts",
  contact: (id: string) => `/contacts/${seg(id)}`,
  growthReport: "/growth-report",
  copilotChat: "/copilot/chat",
  /** The same turn as an SSE stream — `token` / `status` frames, then `done` with the reply. */
  copilotChatStream: "/copilot/chat/stream",
  aiUsage: "/ai-usage/summary",

  /* ---------------- Activity / reports / search / chat history ----------- */
  activityRuns: "/activity/runs",
  activityRun: (id: string) => `/activity/runs/${seg(id)}`,
  reportsDashboard: "/reports/dashboard",
  /** legacy alias kept so existing hooks don't fork */
  dashboard: "/reports/dashboard",
  analysisInsightDigest: "/analysis/insight-digest",
  analysisPipelineFunnel: "/analysis/pipeline-funnel",
  analysisResponseRate: "/analysis/response-rate",
  monitoringHealthReport: "/monitoring/health-report",
  rateLimitStatus: "/rate-limit/status",
  conversations: "/conversations",
  conversation: (id: string) => `/conversations/${seg(id)}`,
  conversationMessages: (id: string) => `/conversations/${seg(id)}/messages`,
  search: "/search",

  /* ---------------- Long-term memory (what the agents remember) ----------- */
  memories: "/memories",
  memory: (id: string) => `/memories/${seg(id)}`,

  /* ---------------- Data portability (13.1-13.3) ------------------------- */
  dataExport: "/data-portability/export",
  dataImportPlan: "/data-portability/import-plan",
  dataRedact: "/data-portability/redact",

  /* ---------------- Salary & offers (12.1-12.5) ------------------------ */
  offerSalaryBenchmark: "/offers/salary-benchmark",
  offerNegotiate: "/offers/negotiate",
  offerCompare: "/offers/compare",
  offerCounterOffer: "/offers/counter-offer",

  /* ---------------- Granular growth engines (10.1-10.13) --------------- */
  growthGapAnalysis: "/growth/gap-analysis",
  growthReadiness: "/growth/readiness",
  growthLearningPlan: "/growth/learning-plan",
  growthSkillDemand: "/growth/skill-demand",
  growthLearningPriority: "/growth/learning-priority",
  growthProgression: "/growth/progression",
  growthInterviewPrep: "/growth/interview-prep",
  growthStoryBank: "/growth/story-bank",
  growthRoleSuggestions: "/growth/role-suggestions",
  growthProgress: "/growth/progress",
  companyBrief: "/companies/brief",
  outreachDraft: "/outreach/draft",

  /* ---------------- Job ingestion (14.2-14.3) --------------------------- */
  jobIngestParse: "/jobs/ingest/parse",
  jobIngestDedupe: "/jobs/ingest/dedupe",
  jobIngestFreshness: "/jobs/ingest/freshness-sweep",
  jobIngestPlan: "/jobs/ingest/plan",

  /** SSE stream for any async AI task (match, tailor, copilot turn, ingestion…) */
  aiStream: (taskId: string) => `/ai/stream/${seg(taskId)}`,
} as const;

export function apiUrl(path: string): string {
  return `${API_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
}
