import { request } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import { tokenStore } from "@/lib/api/token-store";

import type { Locale } from "./translations";

/**
 * The account's copy of the language (roadmap 21.4).
 *
 * The cookie is the browser's copy: it paints the first render and never leaves the machine.
 * The account's copy is the one the nightly letter can read -- a sweep has no browser, so
 * without it the letter was English whatever the reader had chosen. This module is the bridge
 * between the two, kept out of the provider so the i18n layer stays a render concern.
 */

/** The two languages the product speaks, or null for anything else. */
export function asLocale(value: unknown): Locale | null {
  return value === "en" || value === "zh" ? value : null;
}

export type LocaleDecision =
  | { action: "none" }
  | { action: "adopt"; locale: Locale }
  | { action: "save"; locale: Locale };

/**
 * What this browser owes the account, given both copies and the screen's language.
 *
 * - The account names no known language: nothing to do (an older backend, or a row the
 *   request has not answered yet).
 * - This browser has a choice of its own: it is the reader's most recent instruction, so it
 *   is pushed to the account when the two disagree. That is also what makes a switch in the
 *   app reach the letter.
 * - This browser never chose: it paints whatever the account says. Adopting it quietly --
 *   cookie and screen, not `localStorage` -- keeps the browser free to follow a later change
 *   made elsewhere.
 */
export function decideLocale(
  account: unknown,
  current: Locale,
  chosen: Locale | null
): LocaleDecision {
  const language = asLocale(account);
  if (!language) return { action: "none" };
  if (chosen) {
    return chosen === language ? { action: "none" } : { action: "save", locale: chosen };
  }
  return language === current ? { action: "none" } : { action: "adopt", locale: language };
}

/**
 * Write one language onto the account, when there is an account to write to.
 *
 * A signed-out reader has only the cookie; that is not a failure, it is the anonymous half of
 * the product. A rejected write is the caller's to swallow: the cookie still speaks for this
 * browser, and the next switch (or the next visit) tries again.
 */
export async function saveLocalePreference(locale: Locale): Promise<void> {
  if (!tokenStore.hasSession()) return;
  await request<unknown>(endpoints.auth.me, { method: "PATCH", body: { locale } });
}
