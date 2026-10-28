import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

import { stripComments } from "@/lib/i18n/copy-scan";
import { translations } from "@/lib/i18n/translations";

/**
 * A write's failure sentence is a key, not an English line.
 *
 * `fail()` and `describe()` are the one place a broken write becomes a
 * sentence the reader sees. The sentence is resolved when the toast is
 * raised -- from an event handler, long after the render that knew the
 * reader's language -- so the fallback a call site passes has to be a key
 * the table answers in both languages. An English literal there is one
 * sentence a Chinese reader never gets, and nothing else in the suite looks
 * at these calls: the used-keys gate only reads `t()`/`translate()` keys,
 * and the toast census only reads successful writes.
 *
 * The population is the browser's own sources. Every `fail(` call has to
 * pass a literal key -- or the same key inside `translate(...)`, the shape
 * a hook written before this gate may still use. A call the scanner cannot
 * read is refused rather than skipped, because a site it cannot read is
 * exactly where an English sentence would hide.
 *
 * The other direction -- every key in the `failures` namespace is asked for
 * -- is not checked: the namespace is the fallback shelf, and a sentence
 * that stops being asked for is a sentence to delete, not a gate failure.
 */

const ROOT = fileURLToPath(new URL("../../", import.meta.url));

/** The module that defines the two functions; its own call is the seam. */
const DEFINITION = "lib/hooks/failure.ts";

/** A dotted key: a namespace and a name, starting lower-case. */
const KEY = /^[a-z][A-Za-z0-9]*(?:\.[A-Za-z0-9]+)+$/;

const FAIL_CALL = /\bfail\(/g;
const FAIL_KEY = /\bfail\(\s*(?:"([^"]+)"|translate\(\s*"([^"]+)")/g;
const DESCRIBE_CALL = /\bdescribe\(/g;
const DESCRIBE_ARGS = /\bdescribe\(\s*[A-Za-z0-9_.]+\s*(?:,\s*"([^"]+)")?\s*\)/g;

/** Every source file the browser ships, tests aside. */
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

/** The keys of a table, dotted. */
function keysOf(value: unknown, prefix = ""): string[] {
  if (typeof value !== "object" || value === null) return [prefix];
  return Object.entries(value as Record<string, unknown>).flatMap(([k, v]) =>
    keysOf(v, prefix ? `${prefix}.${k}` : k)
  );
}

interface Site {
  file: string;
  key: string;
}

/**
 * Every `fail(...)` call, and the key it names.
 *
 * `unreadable` counts the calls the scanner could not bind to a literal: a
 * call with a variable, a template, or a sentence-shaped second argument.
 */
function failCalls(): { sites: Site[]; unreadable: string[]; files: Set<string> } {
  const sites: Site[] = [];
  const unreadable: string[] = [];
  const files = new Set<string>();
  for (const file of browserSources()) {
    if (file === DEFINITION) continue;
    const source = stripComments(readFileSync(join(ROOT, file), "utf-8"));
    const calls = [...source.matchAll(FAIL_CALL)].length;
    const keys = [...source.matchAll(FAIL_KEY)];
    for (const m of keys) sites.push({ file, key: m[1] ?? m[2] });
    if (keys.length) files.add(file);
    if (calls !== keys.length) {
      unreadable.push(
        `${file}: ${calls - keys.length} of ${calls} fail() call(s) pass something the gate cannot read as a key`
      );
    }
  }
  return { sites, unreadable, files };
}

/** Every `describe(...)` call's literal fallback, when it has one. */
function describeCalls(): { keys: Site[]; unreadable: string[] } {
  const keys: Site[] = [];
  const unreadable: string[] = [];
  for (const file of browserSources()) {
    if (file === DEFINITION) continue;
    const source = stripComments(readFileSync(join(ROOT, file), "utf-8"));
    const calls = [...source.matchAll(DESCRIBE_CALL)].length;
    const matched = [...source.matchAll(DESCRIBE_ARGS)];
    for (const m of matched) if (m[1] !== undefined) keys.push({ file, key: m[1] });
    if (calls !== matched.length) {
      unreadable.push(`${file}: ${calls - matched.length} describe() call(s) do not read as name-or-key`);
    }
  }
  return { keys, unreadable };
}

const en = new Set(keysOf(translations.en));
const zh = new Set(keysOf(translations.zh));

// The scan reads every source file; the four cases ask it the same
// questions, so the answer is kept rather than measured four times.
let failCache: ReturnType<typeof failCalls> | null = null;
let describeCache: ReturnType<typeof describeCalls> | null = null;
const failSurface = () => (failCache ??= failCalls());
const describeSurface = () => (describeCache ??= describeCalls());

describe("the failure sentences the write surface shows", () => {
  it("name a key, not an English sentence", () => {
    const { sites, unreadable } = failSurface();
    expect(unreadable, unreadable.join("\n")).toEqual([]);
    const named = sites.filter((s) => !KEY.test(s.key));
    const offenders = named.map((s) => `${s.file}: fail("${s.key}")`);
    expect(offenders, `a failure passes a sentence where a key belongs:\n${offenders.join("\n")}`).toEqual([]);
  });

  it("resolve in both languages", () => {
    const { sites } = failSurface();
    const { keys: described } = describeSurface();
    const missing = [...sites, ...described]
      .filter((s) => {
        if (!KEY.test(s.key)) return true;
        return !en.has(s.key) || !zh.has(s.key);
      })
      .map((s) => `${s.file}: ${s.key}`);
    expect(missing, `a failure names a key the table does not answer:\n${missing.join("\n")}`).toEqual([]);
  });

  it("keep describe()'s fallback a key too", () => {
    const { keys, unreadable } = describeSurface();
    expect(unreadable, unreadable.join("\n")).toEqual([]);
    const named = keys.filter((s) => !KEY.test(s.key));
    const offenders = named.map((s) => `${s.file}: describe(err, "${s.key}")`);
    expect(offenders, `a describe() fallback is a sentence, not a key:\n${offenders.join("\n")}`).toEqual([]);
  });

  it("were read from the whole write surface, not a corner of it", () => {
    const { sites, files } = failSurface();
    // The census above is only worth its reach: a scan that finds ten sites
    // is not reading the hooks this product writes through.
    expect(sites.length).toBeGreaterThan(60);
    for (const file of [
      "lib/hooks/actions.ts",
      "lib/hooks/data-portability.ts",
      "lib/hooks/growth.ts",
      "lib/hooks/ingestion.ts",
      "lib/hooks/offers.ts",
      "lib/hooks/voice.ts",
      "lib/hooks/notifications.ts",
      "lib/hooks/analytics.ts",
    ]) {
      expect(files.has(file), `${file} carries no failure the gate read`).toBe(true);
    }
    const { keys: described } = describeSurface();
    expect(described.map((s) => s.key)).toContain("failures.profileSave");
  });
});
