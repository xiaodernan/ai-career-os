import { describe, expect, it } from "vitest";

import { LOCALE_COOKIE, localeFromCookie } from "./locale-cookie";
import { translations } from "./translations";

/**
 * The page's title, from the reader's language.
 *
 * The title is rendered into the document's head, and the head is the
 * browser's first paint and the crawler's whole view. So it has to be
 * right in the HTML the *server* sends -- and the server does not know
 * the reader's language, because the product keeps the locale in the
 * browser's own storage.
 *
 * The locale therefore travels in a cookie as well, and this is the part
 * of the arrangement that can go wrong quietly: a cookie that is written
 * but never read, a cookie that names a language the table does not have,
 * a cookie that is scoped so the server never sees it.
 */

/** The locale a cookie value names -- and only the two the product has. */
describe("the locale cookie", () => {
  it("names the two languages the product has", () => {
    expect(localeFromCookie("en")).toBe("en");
    expect(localeFromCookie("zh")).toBe("zh");
  });

  it("falls back to English for anything else", () => {
    // A cookie that was tampered with, or written by an older version,
    // must not put the table into a state it cannot read.
    expect(localeFromCookie("fr")).toBe("en");
    expect(localeFromCookie("")).toBe("en");
    expect(localeFromCookie(undefined)).toBe("en");
    expect(localeFromCookie(null)).toBe("en");
  });

  it("is written for the whole site", () => {
    // A cookie scoped to one path is invisible to the server for every
    // other route, and the title would be English on all of them.
    expect(LOCALE_COOKIE).toBe("careeros.locale");
  });
});

describe("the title table", () => {
  it("names every route the server can be asked for", () => {
    // The keys the route metadata reads, and the two the public pages
    // read. A key that is not in the table would render as the key itself
    // in a browser tab.
    const keys = [
      "nav.activity",
      "nav.applications",
      "nav.companies",
      "nav.copilot",
      "nav.dashboard",
      "nav.growth",
      "nav.interviews",
      "nav.jobs",
      "nav.knowledge",
      "nav.networking",
      "nav.resumes",
      "nav.settings",
      "auth.pageTitles.signIn",
      "auth.pageTitles.signUp",
      "auth.pageTitles.forgotPassword",
      "auth.pageTitles.resetPassword",
      "common.pageNotFound",
      "landing.pageTitle",
    ];
    for (const key of keys) {
      for (const locale of ["en", "zh"] as const) {
        const value = key
          .split(".")
          .reduce<unknown>(
            (acc, part) => (acc as Record<string, unknown>)?.[part],
            translations[locale] as unknown
          );
        expect(typeof value, `${locale}.${key} is not a string`).toBe("string");
        expect((value as string).length, `${locale}.${key} is blank`).toBeGreaterThan(0);
      }
    }
  });
});
