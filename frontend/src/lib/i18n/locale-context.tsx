"use client";

import * as React from "react";
import { translations, type Locale, type TranslationKey } from "./translations";
import { writeLocaleCookie } from "./locale-cookie";

/**
 * Locale context (17.1): provides the current locale and a translation function.
 * The product is CN-context but English content; this context lets the user
 * switch between the two.
 */

interface LocaleContextValue {
  locale: Locale;
  setLocale: (locale: Locale) => void;
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

function getInitialLocale(): Locale {
  if (typeof window === "undefined") return "en";
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored === "en" || stored === "zh") return stored;
  } catch {
    /* ignore */
  }
  return "en";
}

export function LocaleProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocaleState] = React.useState<Locale>(getInitialLocale);

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
  }, []);

  // The cookie is written on the first render too, so a reader whose
  // cookie was cleared but whose localStorage survived still gets a title
  // in their language -- and so a reader who has never chosen sees the
  // default, which is the default everywhere.
  React.useEffect(() => {
    writeLocaleCookie(locale);
  }, [locale]);

  const t = React.useCallback(
    (key: string, vars?: Record<string, string | number>): string => {
      const parts = key.split(".");
      let value: unknown = translations[locale];
      for (const part of parts) {
        if (value != null && typeof value === "object") {
          value = (value as Record<string, unknown>)[part];
        } else {
          return key;
        }
      }
      if (typeof value !== "string") return key;
      if (!vars) return value;
      return value.replace(/\{(\w+)\}/g, (hole, name: string) =>
        Object.prototype.hasOwnProperty.call(vars, name) ? String(vars[name]) : hole,
      );
    },
    [locale]
  );

  const value = React.useMemo(() => ({ locale, setLocale, t }), [locale, setLocale, t]);

  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>;
}

export function useLocale(): LocaleContextValue {
  const ctx = React.useContext(LocaleContext);
  if (!ctx) {
    throw new Error("useLocale must be used within a LocaleProvider");
  }
  return ctx;
}
