import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, api, backoffFor, postSSE, request } from "./client";
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

describe("request() — retry with backoff", () => {
  /**
   * The backoff is real sleeps, so the timers are advanced by hand rather than waited
   * on: 1s + 2s + 4s plus jitter is ten seconds of a suite's life per test, and a test
   * that costs ten seconds does not get run.
   */
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  /** Settles the request promise while advancing every timer the retry schedules. */
  function settle<T>(promise: Promise<T>): Promise<T> {
    const guarded = promise.catch((e) => e);
    return vi.runAllTimersAsync().then(() => guarded) as Promise<T>;
  }

  it("retries a 500 and succeeds when the next attempt answers", async () => {
    mockFetch((_url, i) => (i === 0 ? resp(500, errEnv("BOOM", "database is on fire")) : resp(200, okEnv({ id: 1 }))));
    const data = await settle(request<{ id: number }>("/things"));
    expect(data).toEqual({ id: 1 });
    // one retry, not the full budget: it stopped as soon as the answer arrived.
    expect(calls).toHaveLength(2);
  });

  it("gives up after the budget and reports the last failure", async () => {
    mockFetch(() => resp(503, errEnv("DOWN", "upstream is down")));
    const err = await settle(request("/things").catch((e: unknown) => e));
    expect(err).toBeInstanceOf(ApiError);
    expect((err as ApiError).status).toBe(503);
    // initial attempt + 3 retries = 4, then the error propagates rather than looping.
    expect(calls).toHaveLength(4);
  });

  it("does not retry a 4xx, so a validation failure answers immediately", async () => {
    mockFetch(() => resp(400, errEnv("VALIDATION", "title required")));
    const err = await settle(request("/things").catch((e) => e));
    expect((err as ApiError).status).toBe(400);
    expect(calls).toHaveLength(1);
  });

  it("treats 429 as transient, because that is the one 4xx worth waiting on", async () => {
    mockFetch((_url, i) => (i === 0 ? resp(429, errEnv("RATE_LIMITED", "slow down")) : resp(200, okEnv(null))));
    await settle(request("/things"));
    expect(calls).toHaveLength(2);
  });

  it("retries a network failure, since fetch rejects rather than answering", async () => {
    mockFetch((_url, i) => {
      if (i === 0) throw new TypeError("Failed to fetch");
      return resp(200, okEnv({ ok: true }));
    });
    const data = await settle(request("/things"));
    expect(data).toEqual({ ok: true });
    expect(calls).toHaveLength(2);
  });

  it("does not retry an abort, because that is the caller ending the request", async () => {
    // The exception to the network rule: a `signal` abort is the caller's decision, and
    // re-sending it would be the client overriding them.
    mockFetch(() => {
      throw new DOMException("The operation was aborted.", "AbortError");
    });
    const err = (await settle(request("/things").catch((e: unknown) => e))) as DOMException;
    expect(err).toBeInstanceOf(DOMException);
    expect(err.name).toBe("AbortError");
    expect(calls).toHaveLength(1);
  });

  it("doubles the wait between attempts and caps it, so a struggling service recovers", async () => {
    // The doubling and the cap, asserted as arithmetic rather than measured through
    // timers: the shipped delay adds up to 1s of jitter on top, so a timing assertion
    // would only be able to say "somewhere over a second".
    expect(backoffFor(0)).toBe(1_000);
    expect(backoffFor(1)).toBe(2_000);
    expect(backoffFor(2)).toBe(4_000);
    // ...and it stops growing: 8s, 16s and beyond are all held at the ceiling.
    expect(backoffFor(3)).toBe(8_000);
    expect(backoffFor(10)).toBe(10_000);
  });
});

describe("download() — the file arrives as bytes", () => {
  interface FileResponse extends FakeResponse {
    blob: () => Promise<Blob>;
    headers: { get: (name: string) => string | null };
  }
  const fileResp = (status: number, body: Blob | unknown, disposition: string | null): FileResponse => ({
    status,
    ok: status >= 200 && status < 300,
    json: async () => body,
    blob: async () => body as Blob,
    headers: {
      get: (name) => (name.toLowerCase() === "content-disposition" ? disposition : null),
    },
  });

  it("returns the bytes and the RFC 5987 name, carrying the bearer token", async () => {
    tokenStore.set("ACC", "REFRESH");
    const bytes = new Blob(["%PDF-1.4 fake bytes"]);
    mockFetch(() => fileResp(200, bytes, "attachment; filename*=UTF-8''my%20resume.pdf"));
    const out = await api.download("/resumes/1/file");
    expect(out.blob).toBe(bytes);
    expect(out.name).toBe("my resume.pdf");
    expect(calls[0].init.headers.get("Authorization")).toBe("Bearer ACC");
  });

  it("falls back to a null name when the disposition is missing", async () => {
    mockFetch(() => fileResp(200, new Blob(["x"]), null));
    const out = await api.download("/resumes/1/file");
    expect(out.name).toBeNull();
  });

  it("parses the envelope error body a file route answers with", async () => {
    tokenStore.set("ACC", "REFRESH");
    mockFetch(() => fileResp(404, errEnv("RESUME_NOT_FOUND", "no file behind it"), null));
    await expect(api.download("/resumes/1/file")).rejects.toMatchObject({
      name: "ApiError",
      code: "RESUME_NOT_FOUND",
      status: 404,
    });
  });

  it("refreshes once on a 401, then retries the original download", async () => {
    tokenStore.set("OLD", "REFRESH");
    mockFetch((_url, i) => {
      if (i === 0) return fileResp(401, errEnv("UNAUTHORIZED", "expired"), null);
      if (i === 1) return resp(200, okEnv({ accessToken: "NEW", refreshToken: "REFRESH2" }));
      return fileResp(200, new Blob(["bytes"]), "attachment; filename*=UTF-8''a.pdf");
    });
    const out = await api.download("/resumes/1/file");
    expect(out.name).toBe("a.pdf");
    expect(calls).toHaveLength(3);
    expect(calls[2].init.headers.get("Authorization")).toBe("Bearer NEW");
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
