import { afterEach, describe, expect, it, vi } from "vitest";

import { fetchMemories, mapMemories } from "@/lib/hooks/resources";

/**
 * What `GET /memories` answers (ai-service `MemoryItem`), one row per kind the extractor
 * writes. camelCase, unlike every backend record in this repo — that mismatch is the reason
 * `mapMemories` exists as more than a passthrough.
 */
const ROW = {
  id: "m1", kind: "skill", key: "kafka", content: "Kafka at scale",
  importance: 0.8, source: "conversation",
  createdAt: "2026-10-01T00:00:00Z", updatedAt: "2026-10-02T00:00:00Z",
};

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

describe("mapMemories", () => {
  it("reads both the bare array and the envelope's own {items}", () => {
    expect(mapMemories([ROW]).length).toBe(1);
    expect(mapMemories({ items: [ROW] }).length).toBe(1);
  });

  it("keeps every field the correction surface needs", () => {
    const [row] = mapMemories({ items: [ROW] });
    expect(row).toEqual({
      id: "m1", kind: "skill", key: "kafka", content: "Kafka at scale",
      importance: 0.8, source: "conversation",
      createdAt: "2026-10-01T00:00:00Z", updatedAt: "2026-10-02T00:00:00Z",
    });
  });

  it("answers an empty list rather than throwing on a shape it does not recognise", () => {
    expect(mapMemories({})).toEqual([]);
    expect(mapMemories(null)).toEqual([]);
  });
});

describe("fetchMemories — the kinds filter", () => {
  it("omits the parameter when no kinds are wanted", async () => {
    mockFetch({ items: [ROW] });
    await fetchMemories();
    // `buildUrl` drops an undefined value, so no `kinds` reaches the wire. This is the
    // "every kind" case, and an empty `kinds=` would bind a list holding one empty string
    // and match no row at all — a filter for nothing.
    expect(urls[0]).not.toContain("kinds");
  });

  it("omits the parameter for an empty array, which is the same request", async () => {
    mockFetch({ items: [ROW] });
    await fetchMemories([]);
    expect(urls[0]).not.toContain("kinds");
  });

  it("joins several kinds with a comma, the spelling the handler binds", async () => {
    mockFetch({ items: [ROW] });
    await fetchMemories(["skill", "preference"]);
    expect(urls[0]).toContain("kinds=skill%2Cpreference");
  });
});
