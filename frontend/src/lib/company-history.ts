/**
 * Epic 407 — the reader's own file with one company.
 *
 * The company page could describe what the corpus knows about an employer and
 * never say what the reader had already done with them: two applications and a
 * rehearsal sat on other screens, unconnected to the page the reader opens
 * before an interview. This module is the fold that joins them, and it is
 * arithmetic over rows the page already holds — no endpoint, no model call.
 *
 * A row belongs to the company when its id matches, or — for rows written
 * before the link existed — when its name matches after trimming and folding
 * case. There is no fuzzy matching: a misspelling is a different company, and
 * guessing one would put somebody else's history in the file. A rehearsal
 * belongs when it names the company or when it was started from an application
 * already in the file. A row with no readable stamp cannot be placed in a
 * chronology and is left out of the list and the counts rather than dated by
 * guesswork.
 */

import type { Application, InterviewSession } from "@/lib/api/types";

export type CompanyTouchKind = "application" | "interview";

export interface CompanyTouch {
  id: string;
  kind: CompanyTouchKind;
  /** The ISO moment the row itself carries; every touch in the list is dated. */
  at: string;
  /** The row's own title (a role, a session's job title); may be empty. */
  title: string;
  /** The row's own vocabulary — a stage or a mode — left for the page to translate. */
  word?: string;
  href: string;
}

export interface CompanyHistory {
  /** Newest first. */
  touches: CompanyTouch[];
  applicationCount: number;
  interviewCount: number;
  latest: CompanyTouch | null;
}

export interface CompanyHistoryInput {
  companyId: string;
  companyName: string;
  applications?: Application[];
  interviews?: InterviewSession[];
}

/** The comparison a person makes: trim the ends, fold the case, nothing else. */
export function sameCompany(a: string | null | undefined, b: string | null | undefined): boolean {
  if (!a || !b) return false;
  const left = a.trim().toLocaleLowerCase();
  const right = b.trim().toLocaleLowerCase();
  return left.length > 0 && left === right;
}

function stampOf(value: string | null | undefined): number | null {
  if (!value) return null;
  const at = new Date(value).getTime();
  return Number.isFinite(at) ? at : null;
}

export function companyHistory(input: CompanyHistoryInput): CompanyHistory {
  const touches: CompanyTouch[] = [];
  const applicationIds = new Set<string>();

  const named = (application: Application) =>
    sameCompany(application.companyName ?? application.company?.name, input.companyName);

  for (const application of input.applications ?? []) {
    const byId = Boolean(application.companyId && input.companyId && application.companyId === input.companyId);
    if (!byId && !named(application)) continue;
    // The link is kept even when the row cannot be dated, so a rehearsal started
    // from it still lands in this company's file.
    applicationIds.add(application.id);
    const at = application.appliedAt ?? application.createdAt ?? application.updatedAt ?? null;
    if (!at || stampOf(at) === null) continue;
    touches.push({
      id: `application-${application.id}`,
      kind: "application",
      at,
      title: application.title,
      word: application.status,
      href: `/applications?application=${application.id}`,
    });
  }

  for (const session of input.interviews ?? []) {
    const linked = Boolean(session.applicationId && applicationIds.has(session.applicationId));
    if (!linked && !sameCompany(session.companyName, input.companyName)) continue;
    if (!session.startedAt || stampOf(session.startedAt) === null) continue;
    touches.push({
      id: `interview-${session.id}`,
      kind: "interview",
      at: session.startedAt,
      title: session.jobTitle ?? "",
      word: session.mode,
      href: `/interviews/${session.id}`,
    });
  }

  touches.sort((a, b) => (stampOf(b.at) ?? 0) - (stampOf(a.at) ?? 0));
  const applicationCount = touches.filter((touch) => touch.kind === "application").length;
  return {
    touches,
    applicationCount,
    interviewCount: touches.length - applicationCount,
    latest: touches[0] ?? null,
  };
}
