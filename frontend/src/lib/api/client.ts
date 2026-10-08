import { API_BASE_URL, endpoints } from "./endpoints";
import { tokenStore } from "./token-store";
import type { AuthResponse, AuthTokens, Page, User } from "./types";
import { SESSION_EXPIRED_REASON } from "../session-expiry";
import { dispatchEvent, errorText, findFrameEnd, parseFrame, type SSEHandlers } from "../sse/use-sse";
export interface ApiErrorDetails {
  code: string;
  message: string;
  details?: unknown;
  status: number;
}

/** Structured error from the backend envelope: {success:false, error:{code,message,details}} */
export class ApiError extends Error implements ApiErrorDetails {
  code: string;
  details?: unknown;
  status: number;

  constructor(code: string, message: string, status: number, details?: unknown) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
    this.details = details;
  }

  get isUnauthorized() {
    return this.status === 401;
  }
  get isNotFound() {
    return this.status === 404;
  }
}

interface Envelope<T> {
  success: boolean;
  data: T | null;
  error: { code?: string; message?: string; details?: unknown } | null;
}

export interface RequestOptions extends Omit<RequestInit, "body"> {
  /** JSON body — serialized automatically */
  body?: unknown;
  /** Query params appended to the path */
  params?: Record<string, string | number | boolean | undefined>;
  /** Set false for public endpoints (login/register/refresh) */
  auth?: boolean;
  /** Internal: prevents infinite refresh loops */
  _retry?: boolean;
}

function buildUrl(path: string, params?: RequestOptions["params"]): string {
  const base = path.startsWith("http") ? path : `${API_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
  const url = new URL(base);
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined) url.searchParams.set(k, String(v));
    }
  }
  return url.toString();
}

/* ------------------------------------------------------------------ */
/* Automatic refresh-on-401 with a shared in-flight promise queue.     */
/* ------------------------------------------------------------------ */

let refreshInFlight: Promise<string | null> | null = null;

async function runRefresh(): Promise<string | null> {
  const refreshToken = tokenStore.getRefresh();
  if (!refreshToken) return null;
  try {
    const res = await fetch(buildUrl(endpoints.auth.refresh), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refreshToken }),
    });
    const json = (await res.json()) as Envelope<AuthTokens>;
    if (!res.ok || !json.success || !json.data) return null;
    tokenStore.set(json.data.accessToken, json.data.refreshToken);
    return json.data.accessToken;
  } catch {
    return null;
  }
}

function refreshOnce(): Promise<string | null> {
  // Concurrent 401s share one refresh call; they all await it (the "queue").
  if (!refreshInFlight) {
    refreshInFlight = runRefresh().finally(() => {
      refreshInFlight = null;
    });
  }
  return refreshInFlight;
}

function onSessionExpired() {
  tokenStore.clear();
  if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
    const next = encodeURIComponent(window.location.pathname + window.location.search);
    window.location.href = `/login?next=${next}&reason=${SESSION_EXPIRED_REASON}`;
  }
}

/* ------------------------------------------------------------------ */
/* Core fetch wrapper                                                   */
/* ------------------------------------------------------------------ */

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { body, params, auth = true, _retry = false, headers, ...rest } = options;

  const finalHeaders = new Headers(headers);
  finalHeaders.set("Accept", "application/json");
  if (body !== undefined && !(body instanceof FormData)) {
    finalHeaders.set("Content-Type", "application/json");
  }
  const token = tokenStore.getAccess();
  if (auth && token) finalHeaders.set("Authorization", `Bearer ${token}`);

  const res = await fetch(buildUrl(path, params), {
    ...rest,
    headers: finalHeaders,
    body:
      body === undefined ? undefined : body instanceof FormData ? body : JSON.stringify(body),
  });

  let json: Envelope<T> | null = null;
  try {
    json = (await res.json()) as Envelope<T>;
  } catch {
    /* empty or non-JSON body */
  }

  if (res.status === 401 && auth && !_retry) {
    const newToken = await refreshOnce();
    if (newToken) {
      return request<T>(path, { ...options, _retry: true });
    }
    onSessionExpired();
    throw new ApiError("UNAUTHORIZED", "Your session has expired.", 401);
  }

  if (!res.ok || (json && json.success === false)) {
    const err = json?.error;
    throw new ApiError(
      err?.code ?? (res.status === 404 ? "NOT_FOUND" : "HTTP_ERROR"),
      err?.message ?? `Request failed with status ${res.status}`,
      res.status,
      err?.details,
    );
  }

  return (json?.data ?? (null as T)) as T;
}

/* ------------------------------------------------------------------ */
/* File download — one request, raw bytes                              */
/* ------------------------------------------------------------------ */

/**
 * GET a path that answers with the file itself, never the envelope.
 *
 * The verb, the bearer token and the one refresh-on-401 are {@link request}'s; what differs is the
 * answer: raw bytes, which `EnvelopeAdvice` passes through unwrapped, so there is no envelope to
 * unwrap here and an error body is the only JSON this fetch ever parses. The name comes back from
 * the server's `Content-Disposition` (RFC 5987 spelling, which is the one the backend writes) —
 * the route that read the document row is the one that knows what the file was called.
 */
export async function download(
  path: string,
  options: { _retry?: boolean } = {},
): Promise<{ blob: Blob; name: string | null }> {
  const { _retry = false } = options;
  const finalHeaders = new Headers();
  finalHeaders.set("Accept", "application/octet-stream");
  const token = tokenStore.getAccess();
  if (token) finalHeaders.set("Authorization", `Bearer ${token}`);

  const res = await fetch(buildUrl(path), { headers: finalHeaders });

  if (res.status === 401 && !_retry) {
    const newToken = await refreshOnce();
    if (newToken) return download(path, { _retry: true });
    onSessionExpired();
    throw new ApiError("UNAUTHORIZED", "Your session has expired.", 401);
  }

  if (!res.ok) {
    let json: Envelope<never> | null = null;
    try {
      json = (await res.json()) as Envelope<never>;
    } catch {
      /* a body that is neither envelope nor bytes is not worth a second guess */
    }
    const err = json?.error;
    throw new ApiError(
      err?.code ?? (res.status === 404 ? "NOT_FOUND" : "HTTP_ERROR"),
      err?.message ?? `Request failed with status ${res.status}`,
      res.status,
      err?.details,
    );
  }

  const disposition = res.headers.get("Content-Disposition") ?? "";
  const match = /filename\*=UTF-8''([^;]+)/i.exec(disposition);
  return {
    blob: await res.blob(),
    name: match ? decodeURIComponent(match[1]) : null,
  };
}

/* ------------------------------------------------------------------ */
/* Streaming POST — one request, many frames                           */
/* ------------------------------------------------------------------ */

/**
 * POST a path that answers with `text/event-stream`.
 *
 * The verb, the bearer token and the one refresh-on-401 are {@link request}'s: a stream is the
 * same request that simply does not finish. What differs is the answer. Instead of one envelope,
 * the body is a sequence of SSE frames handed to `handlers` as they arrive, and the promise
 * settles on the frame that ends the turn — `done` resolves with its payload, `error` rejects
 * with the cause that frame carries. A stream that closes without either frame is a broken
 * connection, not an empty answer, so it rejects too.
 *
 * `endpoints.copilot/chat/stream` is the caller today: the reply arrives token by token while
 * the agent works, and the stored answer comes back on `done`.
 */
export async function postSSE<T>(
  path: string,
  options: Omit<RequestOptions, "params"> = {},
  handlers: SSEHandlers = {},
): Promise<T> {
  const { body, auth = true, _retry = false, headers, ...rest } = options;

  const finalHeaders = new Headers(headers);
  finalHeaders.set("Accept", "text/event-stream");
  if (body !== undefined) finalHeaders.set("Content-Type", "application/json");
  const token = tokenStore.getAccess();
  if (auth && token) finalHeaders.set("Authorization", `Bearer ${token}`);

  const res = await fetch(buildUrl(path), {
    ...rest,
    method: rest.method ?? "POST",
    headers: finalHeaders,
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  if (res.status === 401 && auth && !_retry) {
    const newToken = await refreshOnce();
    if (newToken) return postSSE<T>(path, { ...options, _retry: true }, handlers);
    onSessionExpired();
    throw new ApiError("UNAUTHORIZED", "Your session has expired.", 401);
  }

  const stream = res.body;
  if (!res.ok || !stream) {
    let json: Envelope<T> | null = null;
    try {
      json = (await res.json()) as Envelope<T>;
    } catch {
      /* empty or non-JSON body */
    }
    const err = json?.error;
    throw new ApiError(
      err?.code ?? (res.status === 404 ? "NOT_FOUND" : "HTTP_ERROR"),
      err?.message ?? `Request failed with status ${res.status}`,
      res.status,
      err?.details,
    );
  }

  return await new Promise<T>((resolve, reject) => {
    let settled = false;
    const settle = (outcome: () => void) => {
      if (settled) return;
      settled = true;
      outcome();
    };
    const streamHandlers: SSEHandlers = {
      ...handlers,
      onDone: (data) => {
        handlers.onDone?.(data);
        settle(() => resolve(data as T));
      },
      onError: (data) => {
        handlers.onError?.(data);
        settle(() =>
          reject(new ApiError("STREAM_ERROR", errorText(data) ?? "The stream failed.", 502)),
        );
      },
    };

    void (async () => {
      const reader = stream.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      try {
        for (;;) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          let sep: number;
          while ((sep = findFrameEnd(buffer)) !== -1) {
            const frame = buffer.slice(0, sep);
            buffer = buffer.slice(sep).replace(/^\r?\n\r?\n/, "");
            const parsed = parseFrame(frame);
            if (parsed) dispatchEvent(parsed, streamHandlers);
            if (settled) {
              await reader.cancel();
              return;
            }
          }
        }
        settle(() =>
          reject(new ApiError("STREAM_ENDED", "The connection closed before the answer arrived.", 502)),
        );
      } catch (err) {
        settle(() => reject(err));
      }
    })();
  });
}

/* ------------------------------------------------------------------ */
/* Auth API                                                             */
/* ------------------------------------------------------------------ */

export interface LoginPayload {
  email: string;
  password: string;
}
export interface RegisterPayload extends LoginPayload {
  displayName: string;
}

export const authApi = {
  async register(payload: RegisterPayload): Promise<User> {
    const res = await request<AuthResponse>(endpoints.auth.register, {
      method: "POST",
      body: payload,
      auth: false,
    });
    tokenStore.set(res.tokens.accessToken, res.tokens.refreshToken);
    return authApi.me();
  },

  async login(payload: LoginPayload): Promise<User> {
    const res = await request<AuthResponse>(endpoints.auth.login, {
      method: "POST",
      body: payload,
      auth: false,
    });
    tokenStore.set(res.tokens.accessToken, res.tokens.refreshToken);
    return authApi.me();
  },

  async logout(): Promise<void> {
    const refreshToken = tokenStore.getRefresh();
    try {
      await request<void>(endpoints.auth.logout, {
        method: "POST",
        body: { refreshToken },
      });
    } finally {
      tokenStore.clear();
    }
  },

  /**
   * Ask for a reset token. Resolves even for an address with no account: the API answers
   * `{accepted: true}` either way so the screen cannot be used to enumerate users.
   */
  async forgotPassword(payload: { email: string }): Promise<void> {
    await request<{ accepted: boolean }>(endpoints.auth.forgotPassword, {
      method: "POST",
      body: { email: payload.email },
      auth: false,
    });
  },

  /**
   * Spend a reset token. The API revokes every session for the user, so the caller has to
   * send the user back to sign in rather than pretending they are still logged in.
   */
  async resetPassword(payload: { token: string; newPassword: string }): Promise<void> {
    await request<{ reset: boolean }>(endpoints.auth.resetPassword, {
      method: "POST",
      body: { token: payload.token, newPassword: payload.newPassword },
      auth: false,
    });
  },

  me(): Promise<User> {
    return request<User>(endpoints.auth.me);
  },
};

/* ------------------------------------------------------------------ */
/* CRUD helpers                                                        */
/* ------------------------------------------------------------------ */

export interface ListParams {
  page?: number;
  size?: number;
  [filter: string]: string | number | boolean | undefined;
}

export const api = {
  get: <T>(path: string, params?: ListParams) =>
    request<T>(path, { params }),

  list: <T>(path: string, params?: ListParams) =>
    request<Page<T>>(path, { params }),

  create: <T, B = unknown>(path: string, body: B) =>
    request<T>(path, { method: "POST", body }),

  update: <T, B = unknown>(path: string, body: B) =>
    request<T>(path, { method: "PATCH", body }),

  remove: <T = void>(path: string) =>
    request<T>(path, { method: "DELETE" }),

  upload: <T>(path: string, formData: FormData) =>
    request<T>(path, { method: "POST", body: formData }),

  download,

  request,
};
