import { afterEach, describe, expect, it, vi } from "vitest";

import { endpoints } from "@/lib/api/endpoints";

/**
 * Epic 354 — the chronicle route's wire shape. The backend's ChronicleRequest record
 * names `events`, `milestones`, `locale`; a body under the wrong key is a field Jackson
 * drops, so the book is written over an empty ledger.
 */
const okEnv = (data: unknown) => ({ success: true, data, error: null });
let urls: string[] = [];
let bodies: unknown[] = [];

function mockFetch(data: unknown) {
  urls = [];
  bodies = [];
  vi.stubGlobal("fetch", vi.fn(async (url: string, init?: { body?: string }) => {
    urls.push(url);
    if (init?.body) bodies.push(JSON.parse(init.body));
    return { status: 200, ok: true, json: async () => okEnv(data) };
  }));
}

afterEach(() => vi.unstubAllGlobals());

describe("the chronicle route", () => {
  it("posts the events, milestone counters and locale under the bound names", async () => {
    mockFetch({ chapters: [], epilogue: "", locale: "en", empty: true });
    const { api } = await import("@/lib/api/client");

    await api.create(endpoints.timelineChronicle, {
      events: [{ at: "2026-11-10", kind: "application", title: "Applied", refId: "", summary: "" }],
      milestones: { applications: 3 },
      locale: "zh",
    });

    expect(urls[0]).toContain("/timeline/chronicle");
    expect(bodies[0]).toEqual({
      events: [{ at: "2026-11-10", kind: "application", title: "Applied", refId: "", summary: "" }],
      milestones: { applications: 3 },
      locale: "zh",
    });
  });
});
