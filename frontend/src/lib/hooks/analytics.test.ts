import { afterEach, describe, expect, it, vi } from "vitest";

import { endpoints } from "@/lib/api/endpoints";

/**
 * The three analytics endpoints (15.1-15.3) and the two that carry a body
 * (the export bundle and the growth engines).
 *
 * What is worth pinning is the wire shape, not the answers: the routes are
 * read through `api.get` and written through `api.create`, so a body that
 * travels under the wrong key is a field Jackson drops, and a query parameter
 * the endpoint does not bind is a filter that quietly stops filtering.
 */

/** The envelope `api.get` unwraps before a reader sees the payload. */
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

describe("the analytics endpoints", () => {
  it("read their own paths", async () => {
    mockFetch({ totalApplications: 0 });
    const { api } = await import("@/lib/api/client");

    await api.get(endpoints.analysisInsightDigest);
    await api.get(endpoints.analysisPipelineFunnel);
    await api.get(endpoints.analysisResponseRate);

    expect(urls).toEqual([
      expect.stringContaining("/analysis/insight-digest"),
      expect.stringContaining("/analysis/pipeline-funnel"),
      expect.stringContaining("/analysis/response-rate"),
    ]);
  });

  it("send no query parameters, because the digest is computed for the caller", async () => {
    mockFetch({ totalApplications: 0 });
    const { api } = await import("@/lib/api/client");

    await api.get(endpoints.analysisInsightDigest);

    expect(urls[0]).not.toContain("?");
  });
});

describe("the export bundle", () => {
  it("posts the anonymized flag under its own name", async () => {
    mockFetch({ schema_version: "1.0.0" });
    const { api } = await import("@/lib/api/client");

    await api.create(endpoints.dataExport, { anonymized: true });

    expect(urls[0]).toContain("/data-portability/export");
    expect(bodies[0]).toEqual({ anonymized: true });
  });

  it("carries the bundle and the drop list to the redaction route", async () => {
    mockFetch({ schema_version: "1.0.0" });
    const { api } = await import("@/lib/api/client");

    await api.create(endpoints.dataRedact, {
      bundle: { schema_version: "1.0.0" },
      drop: ["interviews"],
    });

    expect(urls[0]).toContain("/data-portability/redact");
    expect(bodies[0]).toEqual({
      bundle: { schema_version: "1.0.0" },
      drop: ["interviews"],
    });
  });
});

describe("the growth engine routes", () => {
  it("post the role under the name their record declares", async () => {
    mockFetch({ targetRole: "Backend Engineer" });
    const { api } = await import("@/lib/api/client");

    await api.create(endpoints.growthGapAnalysis, { targetRole: "Backend Engineer" });
    await api.create(endpoints.growthRoleSuggestions, { top: 5 });

    expect(urls[0]).toContain("/growth/gap-analysis");
    expect(urls[1]).toContain("/growth/role-suggestions");
    expect(bodies[0]).toEqual({ targetRole: "Backend Engineer" });
    expect(bodies[1]).toEqual({ top: 5 });
  });
});

describe("the offer routes", () => {
  it("post the offers as a list, so a grant stays a nested object", async () => {
    mockFetch({ rows: [] });
    const { api } = await import("@/lib/api/client");

    await api.create(endpoints.offerCompare, {
      role: "Backend Engineer",
      offers: [
        {
          label: "Offer A",
          base: 500000,
          bonus: 20000,
          equity: { shares: 1000, strikePrice: 10, currentPrice: 40, vestYears: 4 },
        },
      ],
    });

    expect(urls[0]).toContain("/offers/compare");
    const sent = bodies[0] as { offers: Array<{ equity?: unknown }> };
    expect(sent.offers).toHaveLength(1);
    expect(sent.offers[0].equity).toEqual({
      shares: 1000,
      strikePrice: 10,
      currentPrice: 40,
      vestYears: 4,
    });
  });
});
