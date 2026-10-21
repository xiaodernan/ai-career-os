import { describe, expect, it } from "vitest";

import { NAV_ITEMS } from "@/components/layout/nav";

import { translations, type Locale } from "./translations";

/**
 * The translation table's two halves have to agree.
 *
 * A key that exists in English and not in Chinese renders the English string
 * on a Chinese page — a half-translated product is worse than an untranslated
 * one, because the reader cannot tell which words are missing. The other way
 * round (a key only in Chinese) is dead weight, and it is how a table grows a
 * second spelling of the same sentence.
 */
function keysOf(value: unknown, prefix = ""): string[] {
  if (typeof value !== "object" || value === null) return [prefix];
  return Object.entries(value as Record<string, unknown>).flatMap(([k, v]) =>
    keysOf(v, prefix ? `${prefix}.${k}` : k)
  );
}

const en = keysOf(translations.en);
const zh = keysOf(translations.zh);

/** The string at a dotted key, or undefined. */
function lookup(table: unknown, key: string): string | undefined {
  const value = key
    .split(".")
    .reduce<unknown>(
      (acc, part) => (acc as Record<string, unknown>)?.[part],
      table as Record<string, unknown>
    );
  return typeof value === "string" ? value : undefined;
}

describe("the translation table", () => {
  it("has the same keys in both languages", () => {
    expect(zh.filter((k) => !en.includes(k))).toEqual([]);
    expect(en.filter((k) => !zh.includes(k))).toEqual([]);
  });

  it("has a non-empty string for every key in both languages", () => {
    for (const locale of ["en", "zh"] as Locale[]) {
      const table = translations[locale] as Record<string, unknown>;
      for (const key of en) {
        const value = key
          .split(".")
          .reduce<unknown>((acc, part) => (acc as Record<string, unknown>)?.[part], table);
        expect(typeof value, `${locale}.${key} must be a string`).toBe("string");
        expect((value as string).length, `${locale}.${key} must not be blank`).toBeGreaterThan(0);
      }
    }
  });

  it("does not leave a Chinese string in the English table", () => {
    // A Chinese run in the English table is a key nobody translated, left in
    // place by accident. The English table is the fallback, so it has to be
    // English.
    for (const key of en) {
      const value = key
        .split(".")
        .reduce<unknown>(
          (acc, part) => (acc as Record<string, unknown>)?.[part],
          translations.en as Record<string, unknown>
        );
      expect(/[一-鿿]/.test(value as string), `en.${key} carries Chinese text`).toBe(false);
    }
  });

  it("names every navigation item's label", () => {
    // The sidebar reads the label through a key, so a nav item without one
    // silently keeps its English name on a Chinese page.
    //
    // This walks the *items*, not the table. The other direction -- every key
    // in the table has a Chinese label -- is the wrong half: a table key
    // nobody asks for is dead weight, while a nav item that asks for
    // nothing is a page the reader sees in English on every language. Two
    // items were exactly that, and this test said nothing about them,
    // because it only looked at the table.
    const nav = translations.en.nav as Record<string, string>;
    const navZh = translations.zh.nav as Record<string, string>;
    for (const [key, value] of Object.entries(nav)) {
      expect(navZh[key], `nav.${key} has no Chinese label`).toBeTruthy();
      expect(value.length).toBeGreaterThan(0);
    }

    for (const item of NAV_ITEMS) {
      expect(item.labelKey, `${item.href} names no label`).toBeTruthy();
      expect(
        lookup(translations.en, item.labelKey),
        `${item.labelKey} has no English label`
      ).toBeTruthy();
      expect(
        lookup(translations.zh, item.labelKey),
        `${item.labelKey} has no Chinese label`
      ).toBeTruthy();
    }
  });

  it("has a label for every page that renders one", () => {
    // The page-level blocks are what a page's own heading reads. A page whose
    // block went missing renders the raw key -- "applications.title" -- which
    // the type checker cannot see, because `t()` accepts any string.
    for (const page of ["jobs", "applications", "interviews", "resumes",
                        "settings", "companies", "knowledge", "activity",
                        "growth", "offers", "analysis", "monitoring",
                        "data", "ingestion", "networking", "copilot",
                        "dashboard"]) {
      const block = (translations.en as unknown as Record<string, { title?: string }>)[page];
      expect(block, `${page} has no translation block`).toBeTruthy();
      expect(block!.title, `${page}.title is missing`).toBeTruthy();
      const zhBlock = (translations.zh as unknown as Record<string, { title?: string }>)[page];
      expect(zhBlock, `${page} has no Chinese block`).toBeTruthy();
      expect(zhBlock!.title, `${page}.title has no Chinese label`).toBeTruthy();
    }
  });
});
