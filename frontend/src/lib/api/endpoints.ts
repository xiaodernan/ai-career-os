/**
 * API surface for AI Career OS, derived from docs/architecture.md
 * (§3 module map, §9 conventions). Backend is being built in parallel;
 * when an endpoint 404s the UI must degrade to an EmptyState — never fake data.
 */

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8080/api/v1";

export const endpoints = {
  auth: {
    register: "/auth/register",
    login: "/auth/login",
    refresh: "/auth/refresh",
    logout: "/auth/logout",
    me: "/users/me",
    profile: "/users/me/profile",
  },
  resumes: "/resumes",
  resumeVersions: "/resume-versions",
  jobs: "/jobs",
  savedJobs: "/jobs/saved",
  matches: "/matches",
  jobJds: "/jds",
  applications: "/applications",
  companies: "/companies",
  interviews: "/interview/sessions",
  conversations: "/conversations",
  knowledge: "/knowledge/sources",
  activity: "/activity",
  search: "/search",
  dashboard: "/reports/dashboard",
  /** SSE stream for any async AI task (match, tailor, copilot turn, ingestion…) */
  aiStream: (taskId: string) => `/ai/stream/${encodeURIComponent(taskId)}`,
} as const;

export function apiUrl(path: string): string {
  return `${API_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
}
