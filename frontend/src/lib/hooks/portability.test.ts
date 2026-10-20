import { afterEach, describe, expect, it, vi } from "vitest";

import { endpoints } from "@/lib/api/endpoints";

/**
 * The portability and ingestion bodies.
 *
 * These routes carry free-form documents — a bundle is a bundle, a posting is
 * whatever the source carried — so what is worth pinning is that the wrapper
 * around the free form is right: the named fields go out under their own names,
 * and the document itself stays a document rather than being flattened into
 * the body.
 */

const okEnv = (data: unknown) => ({ success: true, data, error: null });

let urls: string[] = [];
let bodies: unknown[] = [];

function mockFetch(data: unknown) {
  urls = [];
  bodies = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: { body?: string }) => {
      urls.push(url);
      if (init?.body) bodies.push(JSON.parse(init.body));
      return { status: 200, ok: true, json: async () => okEnv(data) };
    })
  );
}

afterEach(() => vi.unstubAllGlobals());

describe("the portability bodies", () => {
  it("carries the bundle as one document, not as spread keys", async () => {
    mockFetch({ schema_version: "1.0.0" });
    const { api } = await import("@/lib/api/client");

    await api.create(endpoints.dataImportPlan, {
      bundle: { schema_version: "1.0.0", data: { profile: { id: "u1" } } },
    });

    expect(urls[0]).toContain("/data-portability/import-plan");
    const sent = bodies[0] as { bundle: { data: Record<string, unknown> } };
    // The bundle's own sections stay nested: a spread would put `data` on the
    // request body, where the backend's record has no field for it.
    expect(sent.bundle.data).toEqual({ profile: { id: "u1" } });
    expect(Object.keys(sent)).toEqual(["bundle"]);
  });

  it("carries the sections to drop as a list", async () => {
    mockFetch({ schema_version: "1.0.0" });
    const { api } = await import("@/lib/api/client");

    await api.create(endpoints.dataRedact, {
      bundle: { schema_version: "1.0.0" },
      drop: ["interviews", "memories"],
    });

    const sent = bodies[0] as { drop: string[] };
    expect(sent.drop).toEqual(["interviews", "memories"]);
  });
});

describe("the ingestion bodies", () => {
  it("carries the postings as a list of whatever the source gave", async () => {
    mockFetch({ unique: [], duplicates: [] });
    const { api } = await import("@/lib/api/client");

    await api.create(endpoints.jobIngestDedupe, {
      postings: [
        { title: "Backend Engineer", company: "FakeCorp", location: "Shanghai" },
        { title: "Backend Engineer", company: "FakeCorp", location: "Beijing" },
      ],
    });

    const sent = bodies[0] as { postings: unknown[] };
    expect(sent.postings).toHaveLength(2);
    // The two postings differ only in location, so the fingerprint must keep
    // them apart — the client does not merge anything, it hands the engine what
    // the source carried.
    expect(sent.postings[0]).not.toEqual(sent.postings[1]);
  });

  it("carries the raw feed and the existing corpus for a plan", async () => {
    mockFetch({ create: [], update: [], close: [] });
    const { api } = await import("@/lib/api/client");

    await api.create(endpoints.jobIngestPlan, {
      feed: "<rss><item><title>Backend Engineer</title></item></rss>",
      source: "rss",
      existing: [{ id: "11111111-1111-1111-1111-111111111111", title: "Backend Engineer" }],
    });

    const sent = bodies[0] as { feed: string; source: string; existing: unknown[] };
    expect(sent.feed).toContain("<rss>");
    expect(sent.source).toBe("rss");
    expect(sent.existing).toHaveLength(1);
  });
});
