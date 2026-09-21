"use client";

/**
 * Token storage: access token lives in-memory (fast, cleared on tab close) with a
 * localStorage fallback so a page reload keeps the session (v1 documented tradeoff,
 * architecture.md §7). Refresh token is persisted so silent refresh survives reloads.
 * Never read localStorage during SSR.
 */

const ACCESS_KEY = "careeros.accessToken";
const REFRESH_KEY = "careeros.refreshToken";

const canUseDOM = () => typeof window !== "undefined";

let memoryAccess: string | null = null;
let memoryRefresh: string | null = null;

function read(key: string): string | null {
  if (!canUseDOM()) return null;
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

function write(key: string, value: string | null) {
  if (!canUseDOM()) return;
  try {
    if (value == null) window.localStorage.removeItem(key);
    else window.localStorage.setItem(key, value);
  } catch {
    /* storage may be blocked (private mode) — in-memory still works */
  }
}

export const tokenStore = {
  getAccess(): string | null {
    return memoryAccess ?? read(ACCESS_KEY);
  },
  getRefresh(): string | null {
    return memoryRefresh ?? read(REFRESH_KEY);
  },
  set(accessToken: string, refreshToken?: string | null) {
    memoryAccess = accessToken;
    write(ACCESS_KEY, accessToken);
    if (refreshToken != null) {
      memoryRefresh = refreshToken;
      write(REFRESH_KEY, refreshToken);
    }
  },
  clear() {
    memoryAccess = null;
    memoryRefresh = null;
    write(ACCESS_KEY, null);
    write(REFRESH_KEY, null);
  },
  hasSession(): boolean {
    return Boolean(this.getAccess());
  },
};
