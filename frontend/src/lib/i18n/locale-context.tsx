"use client";

import * as React from "react";
import { translations, type Locale, type TranslationKey } from "./translations";

/**
 * Locale context (17.1): provides the current locale and a translation function.
 * The product is CN-context but English content; this context lets the user
 * switch between the two.
 */

interface LocaleContextValue {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (key: string) => string;
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
  }, []);

  const t = React.useCallback(
    (key: string): string => {
      const parts = key.split(".");
      let value: unknown = translations[locale];
      for (const part of parts) {
        if (value != null && typeof value === "object") {
          value = (value as Record<string, unknown>)[part];
        } else {
          return key;
        }
      }
      return typeof value === "string" ? value : key;
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
