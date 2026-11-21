import { afterEach, describe, expect, it, vi } from "vitest";

import { endpoints } from "@/lib/api/endpoints";

/**
 * The grounded RAG answer route (knowledge/answer). What is worth pinning is the
 * wire shape: the backend's RagAnswerRequest record names camelCase components and
 * translates them to the ai-service's snake_case fields. A body sent under the
 * wrong key is a field Jackson drops, so the question arrives half-asked.
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

describe("the grounded answer route", () => {
  it("posts the question under the name the backend record binds", async () => {
    mockFetch({ answer: "Grounded [1] answer.", citations: [] });
    const { api } = await import("@/lib/api/client");
    const { field } = await import("@/lib/api/body");

    await api.create(endpoints.knowledgeAnswer, {
      query: "What backend evidence do I have?",
      ...field("topK", 8),
      ...field("contextSummary", "knowledge page"),
    });

    expect(urls[0]).toContain("/knowledge/answer");
    expect(bodies[0]).toEqual({
      query: "What backend evidence do I have?",
      topK: 8,
      contextSummary: "knowledge page",
    });
  });

  it("omits optional filters that were not supplied", async () => {
    mockFetch({ answer: "", citations: [] });
    const { api } = await import("@/lib/api/client");
    const { field } = await import("@/lib/api/body");

    await api.create(endpoints.knowledgeAnswer, {
      query: "short",
      ...field("kinds", undefined),
      ...field("documentIds", undefined),
    });

    expect(bodies[0]).toEqual({ query: "short" });
  });
});
