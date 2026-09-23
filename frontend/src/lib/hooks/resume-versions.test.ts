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
  },
  {
    id: "bbbbbbbb-0000-0000-0000-000000000003",
    resumeId: "aaaaaaaa-0000-0000-0000-000000000001",
    label: "v1",
    kind: "original",
    jobId: null,
    createdAt: "2026-09-01T08:05:00Z",
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
    expect(got[1].source).toBe("original");
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
    await expect(fetchResumeVersions("aaaaaaaa-0000-0000-0000-000000000001")).rejects.toThrow();
  });
});
