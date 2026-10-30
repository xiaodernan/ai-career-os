import { API_BASE_URL, endpoints } from "./endpoints";
import { tokenStore } from "./token-store";
import type { AccountSession, AuthResponse, AuthTokens, Page, User } from "./types";
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
/* Retry helpers                                                      */
/* ------------------------------------------------------------------ */

const RETRYABLE_STATUSES = new Set([408, 429, 500, 502, 502, 503, 504]);
const MAX_RETRIES = 3;
const BASE_DELAY_MS = 1000;
const MAX_DELAY_MS = 10000;

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function calculateBackoff(attempt: number): number {
  const delay = Math.min(BASE_DELAY_MS * Math.pow(2, attempt), MAX_DELAY_MS);
  // Add jitter to prevent thundering herd
  return delay + Math.random() * 1000;
}

function isRetryable(error: unknown): boolean {
  if (error instanceof ApiError) {
    return RETRYABLE_STATUSES.has(error.status);
  }
  // A network failure surfaces as a rejection, not an answer: `fetch` throws for DNS,
  // a refused connection and a dropped socket. Nothing about those is a verdict on the
  // request, so they are as worth another attempt as a 503.
  return error instanceof TypeError;
}

/**
 * How long to wait before attempt `n` (0-based): doubling, capped, plus jitter.
 *
 * The jitter is the point of the shape, not decoration: without it every caller that
 * failed against the same struggling service wakes at the same instant and hammers it
 * in lockstep — the exact stampede a backoff exists to prevent.
 */
export function backoffFor(attempt: number): number {
  return Math.min(BASE_DELAY_MS * Math.pow(2, attempt), MAX_DELAY_MS);
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

  const attemptRequest = async (attempt: number): Promise<T> => {
    const finalHeaders = new Headers(headers);
    finalHeaders.set("Accept", "application/json");
    if (body !== undefined && !(body instanceof FormData)) {
      finalHeaders.set("Content-Type", "application/json");
    }
    const token = tokenStore.getAccess();
    if (auth && token) finalHeaders.set("Authorization", `Bearer ${token}`);

    let res: Response;
    try {
      res = await fetch(buildUrl(path, params), {
        ...rest,
        headers: finalHeaders,
        body:
          body === undefined ? undefined : body instanceof FormData ? body : JSON.stringify(body),
      });
    } catch (e) {
      // A refused connection throws rather than answering, so the retry decision has to
      // happen here: without this the TypeError escapes and the attempt never reaches the
      // backoff below. `AbortError` from an explicit `signal` is the exception — that is
      // the caller ending the request on purpose, and retrying it would be disobeying them.
      if (e instanceof DOMException && e.name === "AbortError") throw e;
      if (attempt < MAX_RETRIES) {
        await sleep(backoffFor(attempt) + Math.random() * 1000);
        return attemptRequest(attempt + 1);
      }
      throw e;
    }

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
      const error = envelopeError(json, res.status);

      // Retry logic for transient errors (5xx, 429, 408)
      if (isRetryable(error) && attempt < MAX_RETRIES) {
        const delay = calculateBackoff(attempt);
        await sleep(delay);
        return attemptRequest(attempt + 1);
      }

      throw error;
    }

    return (json?.data ?? (null as T)) as T;
  };

  return attemptRequest(0);
}

/**
 * The one place the envelope's error half is turned into an ApiError.
 *
 * `request`, `postSSE`, `download` and `uploadWithProgress` all need it, and the shape it reads —
 * `{code, message, details}` behind `error`, with `NOT_FOUND` standing in for a bare 404
 * — is the backend's to change, so four copies of these five lines would be four places
 * to forget. Callers that already have the parsed body pass it; the ones that do not pass
 * nothing and get the message derived from the status alone.
 */
export function envelopeError(
  json: { error?: { code?: string; message?: string; details?: unknown } | null } | null,
  status: number,
): ApiError {
  const err = json?.error ?? undefined;
  return new ApiError(
    err?.code ?? (status === 404 ? "NOT_FOUND" : "HTTP_ERROR"),
    err?.message ?? `Request failed with status ${status}`,
    status,
    err?.details,
  );
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
    throw envelopeError(json, res.status);
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
    throw envelopeError(json, res.status);
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
  /**
   * The second factor (36.4): six digits from the authenticator, or a printed recovery
   * code. Absent while the account may have no factor; the sign-in screen adds it only
   * after `MFA_REQUIRED` says the password matched an enrolled account. An `undefined`
   * code is dropped by `JSON.stringify`, so the no-factor login still posts two keys.
   */
  code?: string;
}
export interface RegisterPayload extends LoginPayload {
  displayName: string;
}

/** The second door's status, as `GET /me/mfa` answers it. */
export interface MfaStatus {
  enabled: boolean;
  pending: boolean;
  recoveryCodesRemaining: number;
}

/** The seed and the `otpauth://` URI are two spellings of the same secret, shown once. */
export interface MfaEnrollment {
  secret: string;
  otpauthUri: string;
}

/** The password plus a code: what activation, a reprint and a turn-off each verify. */
export interface MfaProof {
  password: string;
  code: string;
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

  /**
   * Answer the address-move letter (26.2). Public on purpose: possession of the token is
   * the proof, so the new mailbox answers without a session. The API moves `users.email`
   * and revokes every refresh token, so the caller drops its local pair too.
   */
  async confirmEmailChange(payload: { token: string }): Promise<void> {
    await request<{ changed: boolean }>(endpoints.auth.emailChangeConfirm, {
      method: "POST",
      body: { token: payload.token },
      auth: false,
    });
  },

  /**
   * Ask to move the sign-in address (26.1, 38.2). The password is the re-authentication,
   * so a borrowed tab cannot start the move. Two letters leave — the confirmation to the
   * claimed address and a heads-up to the one on the account — and nothing moves until
   * the new mailbox answers, so the caller keeps its session and its cache.
   */
  async requestEmailChange(payload: { password: string; newEmail: string }): Promise<void> {
    await request<{ sent: boolean }>(endpoints.auth.emailChange, {
      method: "POST",
      body: { password: payload.password, newEmail: payload.newEmail },
    });
  },

  /**
   * The account's open doors, newest activity first (25.1, 38.3). One row is one
   * refresh-token family; `current` marks the family this tab's access token belongs to.
   */
  listSessions(): Promise<AccountSession[]> {
    return request<AccountSession[]>(endpoints.auth.sessions);
  },

  /**
   * Close one door by its family id (25.2, 38.3). A family that is not live for this
   * account — a neighbour's or one already closed — is one `404 LOGIN_SESSION_NOT_FOUND`;
   * the screen reads that as "already closed" rather than an error the reader can act on.
   */
  async revokeSession(familyId: string): Promise<void> {
    await request<{ revoked: boolean }>(endpoints.auth.session(familyId), { method: "DELETE" });
  },

  /**
   * Close every door, this tab's included (25.2, 38.3). Refresh tokens die at once; the
   * access token in this tab keeps working until it expires, because access tokens are
   * stateless. The caller says exactly that instead of claiming the tab is logged out.
   */
  async revokeAllSessions(): Promise<void> {
    await request<{ revoked: boolean }>(endpoints.auth.sessions, { method: "DELETE" });
  },

  /**
   * Replace the password (24.1, 38.4). The current password is the re-authentication,
   * so a borrowed tab cannot lock the owner out; the server refuses a new value equal
   * to the old one by name (`PASSWORD_UNCHANGED`) before it writes. A successful change
   * revokes every refresh token the account holds, this tab's family included — the
   * access token already in memory keeps working until it expires.
   */
  async changePassword(payload: { currentPassword: string; newPassword: string }): Promise<void> {
    await request<{ changed: boolean }>(endpoints.auth.password, {
      method: "PATCH",
      body: { currentPassword: payload.currentPassword, newPassword: payload.newPassword },
    });
  },

  /**
   * Erase the account for good (24.2, 38.5). The password is the re-authentication and
   * the typed-back address the deliberate second act; the server deletes the files the
   * account's documents name and then the row every other row cascades from. Nothing in
   * the answer names either value, and the caller must drop its token pair and cache the
   * moment it resolves — the account whose rows just left cannot refresh.
   */
  async eraseAccount(payload: { password: string; confirmEmail: string }): Promise<void> {
    await request<{ erased: boolean }>(endpoints.auth.erase, {
      method: "POST",
      body: { password: payload.password, confirmEmail: payload.confirmEmail },
    });
  },

  me(): Promise<User> {
    return request<User>(endpoints.auth.me);
  },
};

/* ------------------------------------------------------------------ */
/* The second door (36.1-36.4)                                         */
/* ------------------------------------------------------------------ */

/**
 * The MFA management surface, behind the signed-in session.
 *
 * Every write posts its keys literally: the browser's body gate reads these call sites
 * and holds each name against the record the route binds, so the two cannot drift. The
 * two POSTs that answer recovery codes carry the only copy of that sheet -- the database
 * keeps hashes -- so the screen that calls them has to show it before dropping it.
 */
export const mfaApi = {
  status: () => request<MfaStatus>(endpoints.mfa),

  enroll: () => request<MfaEnrollment>(endpoints.mfaEnroll, { method: "POST" }),

  activate: (proof: MfaProof) =>
    request<{ recoveryCodes: string[] }>(endpoints.mfaActivate, {
      method: "POST",
      body: { password: proof.password, code: proof.code },
    }),

  reissueRecoveryCodes: (proof: MfaProof) =>
    request<{ recoveryCodes: string[] }>(endpoints.mfaRecoveryCodes, {
      method: "POST",
      body: { password: proof.password, code: proof.code },
    }),

  disable: (proof: MfaProof) =>
    request<{ disabled: boolean }>(endpoints.mfaDisable, {
      method: "POST",
      body: { password: proof.password, code: proof.code },
    }),
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

  /**
   * Upload with progress tracking using XMLHttpRequest.
   * Supports progress callbacks for upload progress events.
   */
  uploadWithProgress: <T>(path: string, formData: FormData, onProgress?: (progress: number) => void): Promise<T> => {
    return new Promise<T>((resolve, reject) => {
      const token = tokenStore.getAccess();
      const xhr = new XMLHttpRequest();
      const url = buildUrl(path);

      xhr.open("POST", url, true);

      if (token) {
        xhr.setRequestHeader("Authorization", `Bearer ${token}`);
      }

      xhr.upload.addEventListener("progress", (event) => {
        if (event.lengthComputable && onProgress) {
          onProgress(event.loaded / event.total);
        }
      });

      xhr.addEventListener("load", () => {
        // The answer is gated on the status, exactly as `download` gates its bytes: the
        // success bit is `request`'s and the refresh path's business, and a third copy of
        // that read here would be a third place to forget when the envelope changes.
        let json: { data?: T; error?: { code?: string; message?: string; details?: unknown } } | null = null;
        try {
          json = JSON.parse(xhr.responseText);
        } catch {
          /* no body, or not the envelope — the status alone decides */
        }
        if (xhr.status === 401) {
          // Deliberately not refreshed the way `request` refreshes: the retry would have
          // to re-send the bytes, which is what the refresh-then-retry dance cannot do.
          reject(new ApiError("UNAUTHORIZED", "Your session has expired.", 401));
          return;
        }
        if (xhr.status < 200 || xhr.status >= 300) {
          reject(envelopeError(json, xhr.status));
          return;
        }
        resolve((json?.data ?? null) as T);
      });

      xhr.addEventListener("error", () => {
        reject(new ApiError("NETWORK_ERROR", "Network error during upload", 0));
      });

      xhr.addEventListener("abort", () => {
        reject(new ApiError("ABORTED", "Upload aborted", 0));
      });

xhr.send(formData);
    });
  },

  download,

  request,
};
