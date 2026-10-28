import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it, vi } from "vitest";

import { stripComments } from "@/lib/i18n/copy-scan";
import { translations } from "@/lib/i18n/translations";
import { translate } from "@/lib/i18n/locale-context";

/**
 * The sentence a write raises, and the language it is raised in.
 *
 * A successful write says so with a toast, and the toast is raised from an
 * event handler -- long after the render that knew the language -- so it
 * cannot come from the provider's `t`. It comes from `translate`, which reads
 * the same cookie and `localStorage` the provider writes.
 *
 * The copy census does not read these files: it walks `app/` and
 * `components/`. Every write hook lives in `lib/`, so twenty-seven success
 * toasts were English literals on a Chinese page and no gate looked at them.
 * This one does.
 *
 * The population is every source file the browser ships, and every success
 * toast in it. Failure toasts are a different population with a different
 * writer -- `describe` words them from the error code's own sentence in the
 * table, and the English that remains is a last fallback for a code this
 * build does not know -- so they are not read here. The words that announce
 * *success* are always the product's own, and never the server's.
 */

const ROOT = fileURLToPath(new URL("../../", import.meta.url));

function browserSources(): string[] {
  const out: string[] = [];
  const walk = (dir: string) => {
    for (const entry of readdirSync(dir)) {
      const full = join(dir, entry);
      if (statSync(full).isDirectory()) {
        walk(full);
        continue;
      }
      if (!/\.(ts|tsx)$/.test(entry)) continue;
      if (entry.includes(".test.")) continue;
      out.push(relative(ROOT, full).replace(/\\/g, "/"));
    }
  };
  for (const dir of ["app", "components", "lib"]) walk(join(ROOT, dir));
  return out.sort();
}

/**
 * The string literals in each success toast's argument list.
 *
 * The first version of this gate anchored on a quote right after the
 * parenthesis: `toast.success("Saved.")`. A toast raised with a ternary --
 * `toast.success(saved ? "Removed from saved jobs." : "Saved to your
 * pipeline.")` -- puts an expression there instead, and two English
 * sentences sat in a toast the gate could not read. A green gate over a
 * population it cannot see is the failure this file exists to prevent, so
 * the scan reads the whole argument list, balanced, one call at a time.
 *
 * The walk tracks quotes so a parenthesis inside a sentence does not end the
 * call, and it reads both kinds of string: a double-quoted one and a
 * template. A template carrying `${...}` is not a sentence written in the
 * file but an expression, and the copy filter drops it on its braces.
 */
export function successToastLiterals(source: string): string[] {
  const out: string[] = [];
  for (const m of source.matchAll(/\btoast\.success\s*\(/g)) {
    let i = (m.index ?? 0) + m[0].length;
    let depth = 1;
    while (i < source.length && depth > 0) {
      const ch = source[i];
      if (ch === '"' || ch === "'" || ch === "`") {
        let value = "";
        let j = i + 1;
        while (j < source.length && source[j] !== ch) {
          if (source[j] === "\\") {
            value += source[j + 1] ?? "";
            j += 2;
            continue;
          }
          value += source[j];
          j++;
        }
        // A single-quoted string is an identifier or a character, and never
        // the product's copy: this codebase writes its sentences in double
        // quotes and its templates in backticks.
        if (ch !== "'") out.push(value);
        i = j + 1;
        continue;
      }
      if (ch === "(") depth++;
      else if (ch === ")") depth--;
      i++;
    }
  }
  return out;
}

/**
 * Whether a literal is a sentence the reader sees, rather than a key, an
 * identifier or code that happens to be quoted.
 *
 * A sentence starts with a capital and has a space in it; a key is dotted
 * and lower-case; a template with an expression in it carries braces; and a
 * string holding any character this codebase never writes in prose (a
 * bracket, an equals, a pipe) is code. Chinese is not a sentence in this
 * sense -- it has no capitals -- but a Chinese literal in the source is copy
 * all the same, on the English page, so it counts.
 */
export function isToastCopy(value: string): boolean {
  if (/[\u4e00-\u9fff]/.test(value)) return true;
  if (!/^[A-Z][a-z]/.test(value)) return false;
  if (!/\s/.test(value)) return false;
  return !/[{};=<>|&_]/.test(value);
}

describe("the sentences a write raises", () => {
  it("reads its wording from the table, not from a literal", () => {
    const offenders: string[] = [];
    for (const rel of browserSources()) {
      const source = stripComments(readFileSync(join(ROOT, rel), "utf-8"));
      for (const value of successToastLiterals(source)) {
        if (isToastCopy(value)) offenders.push(`${rel}: "${value}"`);
      }
    }
    expect(
      offenders,
      `a toast says a sentence the reader cannot change:\n${offenders.join("\n")}`,
    ).toEqual([]);
  });

  it("reads a ternary's branches, and leaves a key alone", () => {
    // The control for the widened scan. The anchored version of this gate
    // read neither branch of the first probe -- one expression sat where it
    // expected a quote -- and read the second probe's key as a sentence.
    expect(
      successToastLiterals(`toast.success(saved ? "Removed from saved jobs." : "Saved to your pipeline."),`),
    ).toEqual(["Removed from saved jobs.", "Saved to your pipeline."]);
    expect(successToastLiterals(`toast.success(translate("toasts.contactUpdated"));`)).toEqual([
      "toasts.contactUpdated",
    ]);
    expect(isToastCopy("Removed from saved jobs.")).toBe(true);
    expect(isToastCopy("toasts.contactUpdated")).toBe(false);
  });

  it("reached the end of the write surface", () => {
    // A census of nothing is not a census unless the walk itself is
    // checked: a moved directory or a changed suffix would make the gate
    // above pass by reading nothing. The floor is derived from the file it
    // reads -- one literal per success toast, less the calls whose argument
    // is a bare identifier -- so a walker that stopped at the first call
    // cannot clear it.
    const files = browserSources();
    expect(files).toContain("lib/hooks/actions.ts");
    expect(files.length).toBeGreaterThan(150);

    const actions = stripComments(readFileSync(join(ROOT, "lib/hooks/actions.ts"), "utf-8"));
    const calls = (actions.match(/\btoast\.success\s*\(/g) ?? []).length;
    expect(calls).toBeGreaterThan(20);
    expect(successToastLiterals(actions).length).toBeGreaterThanOrEqual(calls - 2);
  });

  it("answers every toast in the reader's language", () => {
    // `translate` is the path a toast takes. It reads `localStorage`, which
    // the provider writes the moment the reader switches -- so the language
    // is pinned here the way the provider would have pinned it.
    vi.stubGlobal("window", { localStorage: { getItem: () => "zh", setItem: () => {} } });
    try {
      expect(translate("toasts.contactUpdated")).toBe("联系人已更新。");
    } finally {
      vi.unstubAllGlobals();
    }
    // No toast may be the English sentence copied into the Chinese half: a
    // key that exists in both languages and reads the same is a key nobody
    // translated.
    for (const [key, en] of Object.entries(translations.en.toasts)) {
      expect(translations.zh.toasts[key as keyof typeof translations.zh.toasts], key).not.toBe(en);
    }
  });
});
