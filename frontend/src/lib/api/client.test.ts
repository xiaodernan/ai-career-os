import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, request } from "./client";
import { tokenStore } from "./token-store";

interface FakeResponse {
  status: number;
  ok: boolean;
  json: () => Promise<unknown>;
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
