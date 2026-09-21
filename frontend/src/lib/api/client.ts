import { API_BASE_URL, endpoints } from "./endpoints";
import { tokenStore } from "./token-store";
import type { AuthTokens, Page, User } from "./types";

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
    window.location.href = `/login?next=${next}`;
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
    const tokens = await request<AuthTokens>(endpoints.auth.register, {
      method: "POST",
      body: payload,
      auth: false,
    });
    tokenStore.set(tokens.accessToken, tokens.refreshToken);
    return authApi.me();
  },

  async login(payload: LoginPayload): Promise<User> {
    const tokens = await request<AuthTokens>(endpoints.auth.login, {
      method: "POST",
      body: payload,
      auth: false,
    });
    tokenStore.set(tokens.accessToken, tokens.refreshToken);
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

  request,
};
