import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, postSSE, request } from "./client";
import { tokenStore } from "./token-store";

interface FakeResponse {
  status: number;
  ok: boolean;
  json: () => Promise<unknown>;
  /** The event-stream body of a 200, absent on every JSON answer. */
  body?: ReadableStream<Uint8Array>;
}
interface Call {
  url: string;
  init: { headers: Headers };
}

const okEnv = (data: unknown) => ({ success: true, data, error: null });
const errEnv = (code: string, message: string) => ({ success: false, data: null, error: { code, message, details: [] } });
const resp = (status: number, body: unknown): FakeResponse => ({
  status,
  ok: status >= 200 && status < 300,
  json: async () => body,
});

/** SSE frames, optionally delivered in the given chunks — a frame split across two reads. */
function sse(chunks: string[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  return new ReadableStream({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(encoder.encode(chunk));
      controller.close();
    },
  });
}
const streamOk = (chunks: string[]): FakeResponse => ({
  status: 200,
  ok: true,
  json: async () => {
    throw new Error("an event stream has no JSON body");
  },
  body: sse(chunks),
});

let calls: Call[] = [];
function mockFetch(handler: (url: string, index: number) => FakeResponse | Promise<FakeResponse>) {
  calls = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init: { headers: Headers }) => {
      calls.push({ url, init });
      return handler(url, calls.length - 1);
    })
  );
}

beforeEach(() => tokenStore.clear());
afterEach(() => vi.unstubAllGlobals());

describe("request() — envelope", () => {
  it("unwraps data and sends the bearer token", async () => {
    tokenStore.set("ACC", "REFRESH");
    mockFetch(() => resp(200, okEnv({ id: 7 })));
    const data = await request<{ id: number }>("/things");
    expect(data).toEqual({ id: 7 });
    expect(calls[0].init.headers.get("Authorization")).toBe("Bearer ACC");
  });

  it("omits Authorization when auth:false", async () => {
    tokenStore.set("ACC", "REFRESH");
    mockFetch(() => resp(200, okEnv(null)));
    await request("/search", { auth: false });
    expect(calls[0].init.headers.get("Authorization")).toBeNull();
  });

  it("serializes params and drops undefined", async () => {
    mockFetch(() => resp(200, okEnv(null)));
    await request("/search", { params: { q: "a b", page: 2, skip: undefined }, auth: false });
    expect(calls[0].url).toContain("q=a+b");
    expect(calls[0].url).toContain("page=2");
    expect(calls[0].url).not.toContain("skip");
  });
});

describe("request() — errors", () => {
  it("throws ApiError from the envelope error payload", async () => {
    mockFetch(() => resp(400, errEnv("VALIDATION", "email required")));
    await expect(request("/x")).rejects.toMatchObject({
      name: "ApiError",
      code: "VALIDATION",
      status: 400,
      message: "email required",
    });
  });

  it("maps an empty 404 body to NOT_FOUND", async () => {
    mockFetch(() => ({ status: 404, ok: false, json: async () => { throw new Error("no body"); } }));
    const err = (await request("/missing").catch((e) => e)) as ApiError;
    expect(err).toBeInstanceOf(ApiError);
    expect(err.code).toBe("NOT_FOUND");
    expect(err.isNotFound).toBe(true);
  });
});

describe("request() — refresh-on-401", () => {
  it("refreshes once, retries the original request, and persists the new token", async () => {
    tokenStore.set("OLD", "REFRESH");
    mockFetch((_url, i) => {
      if (i === 0) return resp(401, errEnv("UNAUTHORIZED", "expired"));
      if (i === 1) return resp(200, okEnv({ accessToken: "NEW", refreshToken: "REFRESH2" }));
      return resp(200, okEnv({ ok: true }));
    });

    const data = await request<{ ok: boolean }>("/protected");
    expect(data).toEqual({ ok: true });
    expect(calls).toHaveLength(3);
    expect(calls[0].init.headers.get("Authorization")).toBe("Bearer OLD");
    expect(calls[1].url).toContain("/auth/refresh");
    expect(calls[2].init.headers.get("Authorization")).toBe("Bearer NEW");
    expect(tokenStore.getAccess()).toBe("NEW");
  });

  it("clears the session when there is no refresh token", async () => {
    tokenStore.set("OLD"); // access only, no refresh
    mockFetch(() => resp(401, errEnv("UNAUTHORIZED", "expired")));
    const err = (await request("/protected").catch((e) => e)) as ApiError;
    expect(err.code).toBe("UNAUTHORIZED");
    expect(calls).toHaveLength(1); // refresh never fetched
    expect(tokenStore.getAccess()).toBeNull();
  });

  it("does not loop when the retried request still returns 401", async () => {
    tokenStore.set("OLD", "REFRESH");
    mockFetch((_url, i) => {
      if (i === 0) return resp(401, errEnv("UNAUTHORIZED", "expired"));
      if (i === 1) return resp(200, okEnv({ accessToken: "NEW", refreshToken: "REFRESH2" }));
      return resp(401, errEnv("UNAUTHORIZED", "expired")); // retry still fails
    });
    await expect(request("/protected")).rejects.toBeInstanceOf(ApiError);
    // original + refresh + one retry, then stop (the retry carries _retry=true)
    expect(calls).toHaveLength(3);
  });
});

describe("postSSE() — the answer arrives as frames", () => {
  it("hands each frame to its handler and resolves with the done payload", async () => {
    tokenStore.set("ACC", "REFRESH");
    const steps: unknown[] = [];
    const tokens: string[] = [];
    mockFetch(() =>
      streamOk([
        'event: status\ndata: {"agent":"career","step":"Thinking"}\n\n',
        'event: ping\ndata: {}\n\n',
        'event: token\ndata: {"text":"Hel"}\n\n',
        'event: token\ndata: {"text":"lo"}\n\n',
        'event: done\ndata: {"answer":"Hello","run_id":"r1"}\n\n',
      ]),
    );

    const reply = await postSSE<{ answer: string; run_id: string }>(
      "/copilot/chat/stream",
      { method: "POST", body: { message: "hi" } },
      {
        onToken: (t) => tokens.push(t),
        onStatus: (s) => steps.push(s),
      },
    );

    expect(reply).toEqual({ answer: "Hello", run_id: "r1" });
    expect(tokens).toEqual(["Hel", "lo"]);
    expect(steps).toEqual([{ agent: "career", step: "Thinking" }]);
    expect(calls[0].init.headers.get("Accept")).toBe("text/event-stream");
    expect(calls[0].init.headers.get("Content-Type")).toBe("application/json");
    expect(calls[0].init.headers.get("Authorization")).toBe("Bearer ACC");
  });

  it("reads a frame that arrives in pieces across chunk boundaries", async () => {
    const tokens: string[] = [];
    mockFetch(() =>
      streamOk([
        "event: token\nda",
        'ta: {"text":"a"}\n\nevent: token\ndata: {"text":"b"}\n\nev',
        'ent: done\ndata: {"answer":"ab"}\n\n',
      ]),
    );

    const reply = await postSSE<{ answer: string }>("/copilot/chat/stream", { method: "POST" }, {
      onToken: (t) => tokens.push(t),
    });

    expect(reply).toEqual({ answer: "ab" });
    expect(tokens).toEqual(["a", "b"]);
  });

  it("rejects with the cause the error frame carries, and still hands the frame over", async () => {
    let seen: unknown = null;
    mockFetch(() => streamOk(['event: error\ndata: {"error":"model provider timed out"}\n\n']));

    const err = (await postSSE("/copilot/chat/stream", { method: "POST" }, {
      onError: (data) => (seen = data),
    }).catch((e) => e)) as ApiError;

    expect(err).toBeInstanceOf(ApiError);
    expect(err.code).toBe("STREAM_ERROR");
    expect(err.status).toBe(502);
    expect(err.message).toBe("model provider timed out");
    expect(seen).toEqual({ error: "model provider timed out" });
  });

  it("rejects when the connection closes before any terminal frame", async () => {
    mockFetch(() => streamOk(['event: token\ndata: {"text":"half an"}\n\n']));

    const err = (await postSSE("/copilot/chat/stream", { method: "POST" }).catch((e) => e)) as ApiError;

    expect(err).toBeInstanceOf(ApiError);
    expect(err.code).toBe("STREAM_ENDED");
  });

  it("throws the envelope error when the route answers a status instead of a stream", async () => {
    mockFetch(() => resp(404, errEnv("NOT_FOUND", "no route")));

    const err = (await postSSE("/copilot/chat/stream", { method: "POST" }).catch((e) => e)) as ApiError;

    expect(err).toBeInstanceOf(ApiError);
    expect(err.code).toBe("NOT_FOUND");
    expect(err.isNotFound).toBe(true);
  });

  it("refreshes once, retries the stream, and carries the new token", async () => {
    tokenStore.set("OLD", "REFRESH");
    mockFetch((_url, i) => {
      if (i === 0) return resp(401, errEnv("UNAUTHORIZED", "expired"));
      if (i === 1) return resp(200, okEnv({ accessToken: "NEW", refreshToken: "REFRESH2" }));
      return streamOk(['event: done\ndata: {"answer":"ok"}\n\n']);
    });

    const reply = await postSSE<{ answer: string }>("/copilot/chat/stream", { method: "POST" });

    expect(reply).toEqual({ answer: "ok" });
    expect(calls).toHaveLength(3);
    expect(calls[2].init.headers.get("Authorization")).toBe("Bearer NEW");
    expect(tokenStore.getAccess()).toBe("NEW");
  });
});
