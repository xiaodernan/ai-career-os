import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

/**
 * Epic 392 — the Chinese table reads as Chinese.
 *
 * A bilingual product fails quietly when one language borrows the other's
 * prose: the page is "translated", but a Chinese reader still meets "mock",
 * "counsel" or "grace" mid-sentence. This gate reads the shipped string values
 * (comments excluded) and refuses a small list of English words that already
 * have plain Chinese equivalents. Technical names, brands and wire-format
 * identifiers are deliberately not on the list — they are names, not prose.
 */

const BORROWED = [
  "mock",
  "grace",
  "act",
  "counsel",
  "benchmark",
  "sweep",
  "worker",
  "epic",
  "purge",
  "bug",
  "stale",
  "close",
  "flips",
  "yes-or-no",
  "draft",
  "verify",
  "retrieve",
  "render",
  // Epic 459 — abbreviations and product names a Chinese reader should not
  // meet mid-sentence. Each has a plain Chinese word ("职位描述", "招聘方",
  // "编号", "词元", "列表式", "副驾驶") already in common use.
  "jd",
  "hr",
  "id",
  "token",
  "linear",
  "copilot",
];

function withoutComments(source: string): string {
  return source
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/(^|[^:])\/\/.*$/gm, "$1");
}

function valuesOf(file: string): string[] {
  const source = withoutComments(readFileSync(resolve(__dirname, file), "utf8"));
  return [...source.matchAll(/"((?:[^"\\]|\\.)*)"/g)].map((match) => match[1]);
}

describe("the Chinese table", () => {
  it("does not borrow English prose where Chinese already has the word", () => {
    const offenses: string[] = [];
    for (const value of valuesOf("zh.ts")) {
      if (!/[\u4e00-\u9fff]/.test(value)) continue;
      // `{count}` and `{title}` are placeholders, not prose the reader sees.
      // Route paths (/copilot) and wire identifiers (jd_analyze) are names,
      // not borrowed prose, so they are stripped before the word scan.
      const prose = value
        .replace(/\{[^}]*\}/g, " ")
        .replace(/\/[\w\[\]-]+/g, " ")
        .replace(/\b[a-z]+(?:_[a-z]+)+\b/g, " ");
      for (const word of BORROWED) {
        if (new RegExp(`\\b${word}\\b`, "i").test(prose)) {
          offenses.push(`${word} :: ${value.slice(0, 90)}`);
        }
      }
    }
    expect(offenses).toEqual([]);
  });

  it("keeps the English table free of Chinese characters", () => {
    const offenses = valuesOf("en.ts").filter((value) => /[\u4e00-\u9fff]/.test(value));
    expect(offenses).toEqual([]);
  });
});
