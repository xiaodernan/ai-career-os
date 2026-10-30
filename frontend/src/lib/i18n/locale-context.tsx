"use client";

import * as React from "react";
import { translations, type Locale } from "./translations";
import { localeFromCookie, LOCALE_COOKIE, writeLocaleCookie } from "./locale-cookie";

/**
 * Locale context (17.1): provides the current locale and a translation function.
 * The product is CN-context but English content; this context lets the user
 * switch between the two.
 */

interface LocaleContextValue {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  /**
   * Record a language the account chose elsewhere on this browser, without claiming the
   * reader chose it here (roadmap 21.4). It paints the screen and rewrites the cookie, but
   * leaves the `localStorage` choice empty -- so the next switch is still the one that
   * speaks for this browser, and a device that merely adopted the account keeps adopting
   * it as the account changes.
   */
  adoptLocale: (locale: Locale) => void;
  /**
   * Read a string out of the table.
   *
   * `vars` fills `{name}` holes in the string, so a sentence that wraps a value
   * can be written in one language's word order and not another. A hole with no
   * value is left alone rather than blanked -- a missing value should read as
   * missing, not as a sentence with a gap in it.
   */
  t: (key: string, vars?: Record<string, string | number>) => string;
}

const LocaleContext = React.createContext<LocaleContextValue | null>(null);

const STORAGE_KEY = "careeros.locale";

/**
 * The string at a dotted key, or undefined when the table has none.
 *
 * Exported because the rule is worth having in one place: a reader that
 * needs the string has to be able to tell "there is none" from "here is
 * the key", and the provider's `t` shows the key itself.
 */
export function lookup(table: unknown, key: string): string | undefined {
  let value: unknown = table;
  for (const part of key.split(".")) {
    if (value == null || typeof value !== "object") return undefined;
    value = (value as Record<string, unknown>)[part];
  }
  return typeof value === "string" ? value : undefined;
}

/** Fill `{name}` holes in a sentence. */
export function fill(value: string, vars?: Record<string, string | number>): string {
  if (!vars) return value;
  return value.replace(/\{(\w+)\}/g, (hole, name: string) =>
    Object.prototype.hasOwnProperty.call(vars, name) ? String(vars[name]) : hole
  );
}

/**
 * The language this browser chose, or null when it never chose one.
 *
 * Exported because the distinction is a rule, not an implementation detail (roadmap 21.4):
 * `localStorage` holds the reader's own switch and the cookie holds what this browser paints.
 * A device that only adopted the account's language has the cookie and not this, which is
 * how a later account change can still reach it -- and how an explicit switch wins over it.
 */
export function readStoredLocale(): Locale | null {
  if (typeof window === "undefined") return null;
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored === "en" || stored === "zh") return stored;
  } catch {
    /* ignore */
  }
  return null;
}

/**
 * The locale the page paints, read from the cookie the provider writes.
 *
 * Distinct from {@link readStoredLocale}: that one answers "did the reader choose here?",
 * and this one answers "what language is this browser showing?". They differ on a device
 * that only adopted the account's language (21.4) -- it has the cookie and no stored
 * choice -- which is exactly the device whose toast would otherwise arrive in English.
 */
function readLocaleCookie(): Locale | null {
  if (typeof document === "undefined") return null;
  try {
    const entry = document.cookie
      .split(";")
      .map((part) => part.trim())
      .find((part) => part.startsWith(`${LOCALE_COOKIE}=`));
    return entry ? localeFromCookie(entry.slice(LOCALE_COOKIE.length + 1)) : null;
  } catch {
    return null;
  }
}

function getInitialLocale(): Locale {
  return readStoredLocale() ?? readLocaleCookie() ?? "en";
}

/**
 * The language the reader chose, read outside React.
 *
 * A toast is raised from an event handler, long after the render that knew
 * the language -- so the sentence a failure shows cannot come from a hook.
 * The language is global anyway (a cookie and a `localStorage` entry), and
 * this reads both: the reader's own stored choice first, and the cookie the
 * provider also writes when they never made one. Reading only `localStorage`
 * left every sentence raised this way in English on a browser that had
 * adopted the account's language, because the provider paints the cookie
 * and the adopted language never writes a stored choice.
 */
export function currentLocale(): Locale {
  return getInitialLocale();
}

/**
 * Read a string out of the table, outside React.
 *
 * Unlike the provider's `t`, this returns undefined when the table has no
 * such string -- the caller is outside a render, so it has to be able to
 * fall back to something else rather than show a key.
 */
export function translate(
  key: string,
  vars?: Record<string, string | number>
): string | undefined {
  const value = lookup(translations[currentLocale()], key);
  return value === undefined ? undefined : fill(value, vars);
}

/**
 * Put the locale on the document itself.
 *
 * `<html lang>` is what a screen reader takes its pronunciation from — a Chinese page
 * marked `lang="en"` is read aloud with English phonetics — and it is what a translator
 * uses to decide whether to offer one. The server renders it from the cookie; this keeps
 * it true when the reader switches without a reload.
 */
export function applyDocumentLang(locale: Locale): void {
  if (typeof document === "undefined") return;
  document.documentElement.lang = locale;
}

export function LocaleProvider({
  children,
  initialLocale,
}: {
  children: React.ReactNode;
  /** The locale the server read from the cookie — the first render has to match the HTML it sent. */
  initialLocale?: Locale;
}) {
  // Deliberately not `getInitialLocale` when the server named a locale: the browser's copy
  // can disagree with the cookie (one of the two stores was cleared), and a first render
  // that disagrees with the server's markup makes React tear the tree down to hydrate it.
  const [locale, setLocaleState] = React.useState<Locale>(initialLocale ?? getInitialLocale);

  const setLocale = React.useCallback((next: Locale) => {
    setLocaleState(next);
    try {
      window.localStorage.setItem(STORAGE_KEY, next);
    } catch {
      /* ignore */
    }
    // The server's copy of the same fact: the page's title is rendered
    // into the head the browser paints, and the head the server sends is
    // the only one that can be in the reader's language.
    writeLocaleCookie(next);
    applyDocumentLang(next);
  }, []);

  // The account's language reaching a browser that never chose one: paint it and let the
  // next request's server render agree, but do not write the reader's choice -- this browser
  // has not made one, and an `localStorage` entry would keep it from later adopting a change.
  const adoptLocale = React.useCallback((next: Locale) => {
    setLocaleState(next);
    writeLocaleCookie(next);
    applyDocumentLang(next);
  }, []);

  // After hydration the browser's copy wins when it disagrees with the cookie's: it is the
  // copy the reader's own last switch wrote. The cookie is rewritten by the effect below,
  // so the next request's server render agrees.
  React.useEffect(() => {
    const stored = readStoredLocale();
    if (stored && stored !== initialLocale) setLocaleState(stored);
  }, [initialLocale]);

  // The cookie is written on the first render too, so a reader whose
  // cookie was cleared but whose localStorage survived still gets a title
  // in their language -- and so a reader who has never chosen sees the
  // default, which is the default everywhere.
  React.useEffect(() => {
    writeLocaleCookie(locale);
    applyDocumentLang(locale);
  }, [locale]);

  const t = React.useCallback(
    (key: string, vars?: Record<string, string | number>): string => {
      const value = lookup(translations[locale], key);
      if (value === undefined) return key;
      return fill(value, vars);
    },
    [locale]
  );

  const value = React.useMemo(
    () => ({ locale, setLocale, adoptLocale, t }),
    [locale, setLocale, adoptLocale, t]
  );

  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>;
}

export function useLocale(): LocaleContextValue {
  const ctx = React.useContext(LocaleContext);
  if (!ctx) {
    throw new Error("useLocale must be used within a LocaleProvider");
  }
  return ctx;
}
