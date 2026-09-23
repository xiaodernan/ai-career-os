import { describe, expect, it } from "vitest";

import { endpoints } from "./endpoints";

/**
 * Every route the Spring Boot backend actually exposes, under the /api/v1 base
 * (source of truth: the @*Mapping annotations in backend/.../web/*Controller).
 * `*` matches one dynamic path segment (a UUID / task id).
 */
const BACKEND_ROUTES = [
  "/auth/register",
  "/auth/login",
  "/auth/refresh",
  "/auth/logout",
  "/auth/password/forgot",
  "/auth/password/reset",
  "/users/me",
  "/users/me/profile",
  "/resumes",
  "/resumes/upload",
  "/resumes/*",
  "/resumes/*/parse",
  "/resumes/*/set-current",
  "/resumes/*/versions",
  "/resume-versions",
  "/resume-versions/*",
  "/jobs",
  "/jobs/saved",
  "/jobs/import",
  "/jobs/*",
  "/jobs/*/save",
  "/jobs/*/match",
  "/jobs/*/tailor",
  "/jobs/*/tailored-version",
  "/jobs/*/cover-letter",
  "/applications",
  "/applications/*",
  "/applications/*/reorder",
  "/applications/*/timeline",
  "/companies",
  "/companies/*",
  "/interview/sessions",
  "/interview/sessions/*",
  "/interview/sessions/*/opening",
  "/interview/sessions/*/answer",
  "/interview/sessions/*/finalize",
  "/knowledge/sources",
  "/knowledge/sources/*",
  "/knowledge/sources/*/status",
  "/knowledge/notes",
  "/knowledge/notes/*",
  "/knowledge/text",
  "/knowledge/documents",
  "/copilot/chat",
  "/jds",
  "/jds/*",
  "/jds/suggestions",
  "/reports/dashboard",
  "/conversations",
  "/conversations/*",
  "/conversations/*/messages",
  "/search",
  "/ai/stream/*",
  "/ai-usage/summary",
  "/activity/runs",
  "/activity/runs/*",
];

const SAMPLE_ID = "11111111-1111-1111-1111-111111111111";

function toRegex(pattern: string): RegExp {
  const body = pattern
    .split("*")
    .map((part) => part.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))
    .join("[^/]+");
  return new RegExp(`^${body}$`);
}

function collectPaths(node: unknown, out: string[] = []): string[] {
  if (typeof node === "string") out.push(node);
  else if (typeof node === "function") out.push((node as (id: string) => string)(SAMPLE_ID));
  else if (node && typeof node === "object") for (const v of Object.values(node)) collectPaths(v, out);
  return out;
}

describe("endpoints ↔ backend route parity", () => {
  const paths = collectPaths(endpoints);

  it("discovers the full surface", () => {
    expect(paths.length).toBeGreaterThan(30);
  });

  it("every declared endpoint resolves to a real backend route", () => {
    const matchers = BACKEND_ROUTES.map(toRegex);
    const orphans = paths.filter((p) => !matchers.some((re) => re.test(p)));
    expect(orphans).toEqual([]);
  });

  it("no dead routes that the backend removed (regression guards)", () => {
    // These were live-only in the frontend and 404'd against the backend.
    expect(paths).not.toContain("/matches");
    expect(paths).not.toContain("/ai/tailor");
    expect(paths).not.toContain("/ai/cover-letter");
    expect(paths).not.toContain("/ai/suggestions");
    expect(paths.some((p) => p.endsWith("/events"))).toBe(false);
  });
});
