"use client";

import * as React from "react";
import { localeFromCookie, LOCALE_COOKIE, writeLocaleCookie } from "./locale-cookie";
import { installedTable } from "./installed-tables";
import type { Locale, LocaleTable } from "./translations";

/**
 * Locale context (17.1): provides the current locale and a translation function.
 * The product is CN-context but English content; this context lets the user
 * switch between the two.
 *
 * 358: the tables no longer ship with the JavaScript. Both of them did until now,
 * whatever language the page painted, and they are the heaviest thing in the client
 * bundle -- six routes crossed the bundle budget on shared table alone. The reader's
 * own table now arrives with the HTML (the server layout reads the cookie and passes
 * it here), and the other one is a chunk the reader only ever pays for if they
 * switch. Nothing in this module imports a table statically.
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
   * 358: warm the other language's table before the reader commits to it.
   *
   * A switch is a chunk away, so the button that offers one asks for the chunk on
   * hover and focus -- the reader who moves the pointer at the switch pays nothing,
   * and the one who presses it finds the words already there. Nothing else in the
   * app prefetches anything.
   */
  prepareLocale: (locale: Locale) => void;
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
 * The module/table for a TARGET locale, as the chunk webpack splits it into.
 *
 * Named for the locale being loaded, not the one being left. An earlier version
 * took the *current* locale and returned the other one, but `loadSpare` hands it
 * the target — so switching to English imported the Chinese chunk and the reader
 * saw the old language until a reload. The one-click switch only works when the
 * table that lands is the one that was asked for.
 */
const moduleFor = (target: Locale) => (target === "zh" ? import("./zh") : import("./en"));
const tableFor = (target: Locale, mod: { en: LocaleTable; zh: LocaleTable }) =>
  target === "zh" ? mod.zh : mod.en;

/**
 * The table the last render used, for the readers that are outside React.
 *
 * A toast is raised from an event handler, long after the render that knew the
 * language, so `translate` cannot ask a hook. The provider keeps this mirror
 * current on every render; a browser that has rendered nothing yet falls back to
 * whatever table it was handed.
 */
let renderedTable: LocaleTable | undefined;

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
 * A device that only adopted the account's language has the cookie and not this, which
 * is how a later account change can still reach it -- and how an explicit switch wins over it.
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
  // A test installs both tables, and its own locale is the one its cookie names --
  // so the installed table wins there and the answer follows the store. In a browser
  // nothing is installed, and the mirror of the last render is the only table there is.
  const table = installedTable(currentLocale()) ?? renderedTable;
  const value = table === undefined ? undefined : lookup(table, key);
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
  table,
}: {
  children: React.ReactNode;
  /** The locale the server read from the cookie — the first render has to match the HTML it sent. */
  initialLocale?: Locale;
  /**
   * 358: the reader's own table, sent with the HTML. Absent in a test that renders the
   * provider directly, where the installed tables answer instead.
   */
  table?: LocaleTable;
}) {
  const first = initialLocale ?? getInitialLocale();
  // Deliberately not `getInitialLocale` when the server named a locale: the browser's copy
  // can disagree with the cookie (one of the two stores was cleared), and a first render
  // that disagrees with the server's markup makes React tear the tree down to hydrate it.
  const [locale, setLocaleState] = React.useState<Locale>(first);
  // The table the server sent, held once: it belongs to `first`, and a later render must
  // not quietly re-read a prop that only described the first paint.
  const [served] = React.useState<LocaleTable | undefined>(
    () => table ?? installedTable(first)
  );
  // 358: the other language's table, once the reader has asked for it. It arrives as a
  // chunk of its own, so a reader who never switches never downloads it.
  const [spare, setSpare] = React.useState<Partial<Record<Locale, LocaleTable>>>({});

  const loadSpare = React.useCallback(
    (next: Locale): Promise<LocaleTable | undefined> => {
      if (next === first) return Promise.resolve(served);
      const have = spare[next];
      if (have) return Promise.resolve(have);
      return moduleFor(next).then((mod) => {
        const value = tableFor(next, mod as { en: LocaleTable; zh: LocaleTable });
        setSpare((prev) => (prev[next] ? prev : { ...prev, [next]: value }));
        return value;
      });
    },
    [first, served, spare]
  );

  // 358: the table this render speaks. The served one until the reader moves to the
  // other language and its chunk has landed -- and never nothing, because a screen
  // that lost its table would print keys instead of words.
  const active = (locale === first ? served : spare[locale]) ?? served;
  renderedTable = active;

  const apply = React.useCallback((next: Locale) => {
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

  const setLocale = React.useCallback(
    (next: Locale) => {
      // The words are either already here or one chunk away; the stores are written
      // either way, so the next request the server answers is already in the new
      // language even if this screen has not repainted yet.
      if (next === first || spare[next]) {
        apply(next);
        return;
      }
      void loadSpare(next).then((loaded) => {
        if (loaded) apply(next);
      });
    },
    [apply, first, loadSpare, spare]
  );

  // The account's language reaching a browser that never chose one: paint it and let the
  // next request's server render agree, but do not write the reader's choice -- this browser
  // has not made one, and an `localStorage` entry would keep it from later adopting a change.
  const adoptLocale = React.useCallback(
    (next: Locale) => {
      writeLocaleCookie(next);
      applyDocumentLang(next);
      if (next === first || spare[next]) {
        setLocaleState(next);
        return;
      }
      void loadSpare(next).then((loaded) => {
        if (loaded) setLocaleState(next);
      });
    },
    [first, loadSpare, spare]
  );

  const prepareLocale = React.useCallback(
    (next: Locale) => {
      if (next === first || spare[next]) return;
      void loadSpare(next).catch(() => undefined);
    },
    [first, loadSpare, spare]
  );

  // After hydration the browser's copy wins when it disagrees with the cookie's: it is the
  // copy the reader's own last switch wrote. The cookie is rewritten by the effect below,
  // so the next request's server render agrees.
  React.useEffect(() => {
    const stored = readStoredLocale();
    if (stored && stored !== initialLocale) setLocale(stored);
  }, [initialLocale, setLocale]);

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
      const value = active === undefined ? undefined : lookup(active, key);
      if (value === undefined) return key;
      return fill(value, vars);
    },
    [active]
  );

  const value = React.useMemo(
    () => ({ locale, setLocale, adoptLocale, prepareLocale, t }),
    [locale, setLocale, adoptLocale, prepareLocale, t]
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
