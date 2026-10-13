import { afterEach, describe, expect, it, vi } from "vitest";

import { fetchResumeVersions, mapResumeVersions } from "@/lib/hooks/resources";

const okEnv = (data: unknown) => ({ success: true, data, error: null });

let urls: string[] = [];
function mockFetch(data: unknown) {
  urls = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      urls.push(url);
      return { status: 200, ok: true, json: async () => okEnv(data) };
    })
  );
}

afterEach(() => vi.unstubAllGlobals());

/** Exactly what GET /resumes/{id} returns (ResumeDtos.ResumeDetail) — no versions key. */
const RESUME_DETAIL = {
  id: "aaaaaaaa-0000-0000-0000-000000000001",
  title: "resume.pdf",
  status: "parsed",
  currentVersionId: "cccccccc-0000-0000-0000-000000000002",
  createdAt: "2026-09-01T08:00:00Z",
  structured: { profile: { name: "Ada" } },
  experiences: [],
  projects: [],
  educations: [],
  achievements: [],
  skills: [],
};

/** Exactly what GET /resume-versions?resumeId= returns: a BARE List<ResumeVersionItem>. */
const VERSIONS = [
  {
    id: "cccccccc-0000-0000-0000-000000000002",
    resumeId: "aaaaaaaa-0000-0000-0000-000000000001",
    label: "tailored-11111111",
    kind: "tailored",
    jobId: "11111111-0000-0000-0000-000000000000",
    createdAt: "2026-09-02T09:00:00Z",
    diff: {
      accepted: [{ section: "experience", before: "Worked on APIs", after: "Cut p99 by 40%" }],
      rejected: [{ section: "experience", reason: "no evidence" }],
    },
    // A tailored clone has never been parsed, so its version row carries no rubric map.
    score: null,
  },
  {
    id: "bbbbbbbb-0000-0000-0000-000000000003",
    resumeId: "aaaaaaaa-0000-0000-0000-000000000001",
    label: "v1",
    kind: "original",
    jobId: null,
    createdAt: "2026-09-01T08:05:00Z",
    // The map `compute_resume_score` wrote for this version, stored as jsonb and replayed verbatim.
    score: {
      total: 72,
      structure: 62,
      detail: [{ criterion: "quantified_impact", met: false, points: 10 }],
    },
  },
];

describe("mapResumeVersions", () => {
  it("has nothing to read on the resume detail payload", () => {
    // Why the Versions panel was always empty: the detail DTO never carried a versions
    // array, so `versions: mapResumeVersions(body)` was dead by construction.
    expect(mapResumeVersions(RESUME_DETAIL)).toEqual([]);
  });

  it("maps the bare list the versions endpoint actually returns", () => {
    const got = mapResumeVersions(VERSIONS);
    expect(got).toHaveLength(2);
    expect(got[0]).toMatchObject({
      id: "cccccccc-0000-0000-0000-000000000002",
      label: "tailored-11111111",
      createdAt: "2026-09-02T09:00:00Z",
      // the backend names this column `kind`; the panel renders it as `source`
      source: "tailored",
    });
    // the change list the user reviewed has to survive, or the version is a black box
    expect(JSON.stringify(got[0].diff)).toContain("Cut p99 by 40%");
    expect(got[1].diff).toBeUndefined();
    expect(got[1].source).toBe("original");
    // #134: the row shows one score per version, off the same rubric map the resume detail carries.
    // A version that has never been parsed reports none, which the panel must not render as a zero.
    expect(got[0].score).toBeNull();
    expect(got[1].score).toMatchObject({
      overall: 72,
      structure: 62,
      gaps: ["Quantified impact (numbers or %)"],
    });
  });

  it("survives a wrapped or malformed payload without throwing", () => {
    expect(mapResumeVersions({ versions: VERSIONS })[0].label).toBe("tailored-11111111");
    expect(mapResumeVersions(null)).toEqual([]);
    expect(mapResumeVersions({})).toEqual([]);
  });
});

describe("fetchResumeVersions", () => {
  it("requests the resume-scoped versions route", async () => {
    mockFetch(VERSIONS);
    const got = await fetchResumeVersions("aaaaaaaa-0000-0000-0000-000000000001");
    expect(urls[0]).toContain("/resume-versions?");
    expect(urls[0]).toContain("resumeId=aaaaaaaa-0000-0000-0000-000000000001");
    expect(got.map((v) => v.id)).toEqual([
      "cccccccc-0000-0000-0000-000000000002",
      "bbbbbbbb-0000-0000-0000-000000000003",
    ]);
  });

  it("propagates a failed request instead of yielding an empty list", async () => {
    // Swallowing the error would render "No stored versions yet" over real data.
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () => ({
          status: 500,
          ok: false,
          json: async () => ({}),
          headers: new Headers(),
        })
      )
    );
    // A 500 is transient, so `request` retries it three times with an exponential backoff
    // before giving up — 7-10s of real waiting. The timers are advanced by hand so the
    // assertion is about the error propagating, not about how long it takes to arrive.
    vi.useFakeTimers();
    try {
      const outcome = fetchResumeVersions(
        "aaaaaaaa-0000-0000-0000-000000000001"
      ).catch((e) => e);
      await vi.runAllTimersAsync();
      await expect(outcome).resolves.toBeInstanceOf(Error);
    } finally {
      vi.useRealTimers();
    }
  });
});
