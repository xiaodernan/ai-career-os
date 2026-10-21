import type { Locale } from "./translations";

/**
 * The locale cookie.
 *
 * The product keeps the reader's language in the browser's own storage --
 * `localStorage` -- and that is the copy the interface reads. The server
 * cannot see `localStorage`, so it cannot name a page in the reader's
 * language, and the page's title is rendered into the head the browser
 * paints before any script runs.
 *
 * So the same fact travels twice: once in `localStorage`, for the
 * interface, and once in this cookie, for the server. The cookie is
 * written on the first render and on every change, so the two never
 * disagree for long.
 *
 * This module holds the parts both sides need, and nothing server-only --
 * the client writes the cookie, the server reads it, and the read lives
 * in `metadata.ts` with the rest of the server's side.
 */

/** The cookie the locale travels in, alongside the localStorage copy. */
export const LOCALE_COOKIE = "careeros.locale";

/** How long the locale cookie lives: a year, so a reader is not asked again. */
export const LOCALE_COOKIE_MAX_AGE = 60 * 60 * 24 * 365;

/** The locale a cookie value names -- and only the two the product has. */
export function localeFromCookie(value: string | undefined | null): Locale {
  return value === "zh" ? "zh" : "en";
}

/**
 * Write the locale into the cookie the server reads.
 *
 * The localStorage copy is the browser's own; this one is the server's
 * share of the same fact.
 */
export function writeLocaleCookie(locale: Locale): void {
  if (typeof document === "undefined") return;
  try {
    document.cookie = `${LOCALE_COOKIE}=${locale}; path=/; max-age=${LOCALE_COOKIE_MAX_AGE}; samesite=lax`;
  } catch {
    /* ignore */
  }
}
