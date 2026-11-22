import { describe, expect, it } from "vitest";

import { companyHistory, sameCompany } from "@/lib/company-history";
import type { Application, InterviewSession } from "@/lib/api/types";

/**
 * Epic 407 — the company page's own file. Every case here is a row the reader
 * already owns; the fold only decides whether it belongs to this company and
 * where it sits in time. The rule is deliberately narrow: an id match or an
 * exact name after trimming and folding case, never a guess.
 */

function application(overrides: Partial<Application> = {}): Application {
  return {
    id: "a-1",
    title: "Backend Engineer",
    status: "applied",
    companyName: "Acme Robotics",
    createdAt: "2026-11-20T09:00:00Z",
    ...overrides,
  };
}

function session(overrides: Partial<InterviewSession> = {}): InterviewSession {
  return {
    id: "i-1",
    mode: "technical",
    status: "completed",
    jobTitle: "Backend Engineer",
    companyName: "Acme Robotics",
    startedAt: "2026-11-21T10:00:00Z",
    ...overrides,
  };
}

const INPUT = { companyId: "c-1", companyName: "Acme Robotics" };

describe("the company's own file", () => {
  it("joins the applications and rehearsals that name the company, newest first", () => {
    const history = companyHistory({
      ...INPUT,
      applications: [
        application({ id: "a-1", createdAt: "2026-11-20T09:00:00Z" }),
        application({ id: "a-2", title: "Platform Engineer", createdAt: "2026-11-10T09:00:00Z" }),
      ],
      interviews: [session({ id: "i-1", startedAt: "2026-11-21T10:00:00Z" })],
    });
    expect(history.touches.map((touch) => touch.id)).toEqual(["interview-i-1", "application-a-1", "application-a-2"]);
    expect(history.applicationCount).toBe(2);
    expect(history.interviewCount).toBe(1);
    expect(history.latest?.id).toBe("interview-i-1");
    expect(history.touches[1].href).toBe("/applications?application=a-1");
    expect(history.touches[0].href).toBe("/interviews/i-1");
  });

  it("keeps a row whose id matches even when the name was typed differently", () => {
    const history = companyHistory({
      ...INPUT,
      applications: [application({ companyId: "c-1", companyName: "Acme Robotics Ltd." })],
    });
    expect(history.applicationCount).toBe(1);
    expect(history.touches[0].word).toBe("applied");
  });

  it("folds case and trims the ends, and matches nothing else", () => {
    const history = companyHistory({
      ...INPUT,
      applications: [
        application({ id: "a-1", companyName: "  acme ROBOTICS  " }),
        application({ id: "a-2", companyName: "Acme Robotix" }),
        application({ id: "a-3", companyName: null }),
        application({ id: "a-4", companyName: "Acme Robotics Ltd." }),
      ],
    });
    expect(history.touches.map((touch) => touch.id)).toEqual(["application-a-1"]);
    expect(sameCompany("  acme robotics ", "ACM R Obotics")).toBe(false);
    expect(sameCompany(null, "Acme Robotics")).toBe(false);
    expect(sameCompany("   ", "Acme Robotics")).toBe(false);
  });

  it("puts a rehearsal in the file through the application it was started from", () => {
    const history = companyHistory({
      ...INPUT,
      applications: [application({ id: "a-1" })],
      interviews: [session({ id: "i-1", companyName: null, applicationId: "a-1" })],
    });
    expect(history.interviewCount).toBe(1);
    expect(history.touches[0].title).toBe("Backend Engineer");
  });

  it("leaves an undated row out of the list and the counts rather than guessing its day", () => {
    const history = companyHistory({
      ...INPUT,
      applications: [
        application({ id: "a-1", appliedAt: null, createdAt: undefined, updatedAt: undefined }),
        application({ id: "a-2" }),
      ],
      interviews: [session({ id: "i-1", startedAt: undefined })],
    });
    expect(history.touches.map((touch) => touch.id)).toEqual(["application-a-2"]);
    expect(history.applicationCount).toBe(1);
    expect(history.interviewCount).toBe(0);
  });

  it("does not reorder the caller's arrays", () => {
    const applications = [application({ id: "a-1", createdAt: "2026-11-01T00:00:00Z" }), application({ id: "a-2", createdAt: "2026-11-20T00:00:00Z" })];
    companyHistory({ ...INPUT, applications });
    expect(applications.map((row) => row.id)).toEqual(["a-1", "a-2"]);
  });

  it("reports an empty file for a company with no rows", () => {
    expect(companyHistory(INPUT)).toEqual({
      touches: [],
      applicationCount: 0,
      interviewCount: 0,
      latest: null,
    });
  });
});
