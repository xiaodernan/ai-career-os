import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { translations } from "@/lib/i18n/translations";

/**
 * The landing page's copy gate.
 *
 * The landing page is the one page an anonymous visitor can reach, so it is
 * the one page whose language has no signed-in user to switch it. It reads its
 * copy from the locale table like every other surface, and this holds that
 * line: every key the page asks for exists in both languages, and the two are
 * not the same string.
 *
 * The failure this catches is quiet. `t()` accepts any string and returns the
 * key when it cannot find it, so a missing block renders the literal text
 * "landing.features.resume" on the front page and nothing goes red. Type
 * checking cannot see it -- the key is a string, not a union. So the gate
 * reads the page's own source and resolves every key it names.
 */

const SOURCE = readFileSync(
  fileURLToPath(new URL("./landing-page.tsx", import.meta.url)),
  "utf-8"
);

function resolve(locale: "en" | "zh", key: string): unknown {
  let value: unknown = translations[locale];
  for (const part of key.split(".")) {
    if (value == null || typeof value !== "object") return undefined;
    value = (value as Record<string, unknown>)[part];
  }
  return value;
}

/** Every `t("landing....")` the page asks for. */
function landingKeys(): string[] {
  const found = [...SOURCE.matchAll(/t\(\s*["'](landing\.[^"']+)["']\s*\)/g)].map((m) => m[1]);
  return [...new Set(found)].sort();
}

describe("the landing page's copy", () => {
  const keys = landingKeys();

  it("reads its copy from the locale table rather than carrying it", () => {
    // The page has to ask for something -- a gate that passes on zero keys
    // would pass on a page that was emptied out.
    expect(keys.length).toBeGreaterThan(20);
    // And the copy must not also be hardcoded: a key the page reads *and* a
    // literal it prints means the table is not the single source.
    expect(SOURCE).not.toMatch(/description="[A-Z][a-z]+[^"]{20,}"/);
    expect(SOURCE).not.toMatch(/title="[A-Z][a-z]+ [a-z]+"/);
  });

  it("has an English string for every key it asks for", () => {
    const missing = keys.filter((key) => typeof resolve("en", key) !== "string");
    expect(missing).toEqual([]);
  });

  it("has a Chinese string for every key it asks for", () => {
    const missing = keys.filter((key) => typeof resolve("zh", key) !== "string");
    expect(missing).toEqual([]);
  });

  it("does not leave a key untranslated", () => {
    // The same English string in both languages is a key nobody translated.
    // One exception is allowed and it is spelled out: a product name.
    const untranslated = keys.filter(
      (key) => resolve("en", key) === resolve("zh", key) && !/signIn|getStarted/.test(key)
    );
    expect(untranslated).toEqual([]);
  });

  it("offers the visitor a way to switch the language", () => {
    // A public visitor cannot reach the sidebar's switcher, so the page has
    // to carry its own. Without it the Chinese copy is unreachable.
    expect(SOURCE).toContain("setLocale(");
    expect(SOURCE).toContain('t("landing.switchToChinese")');
    expect(SOURCE).toContain('t("landing.switchToEnglish")');
  });
});
