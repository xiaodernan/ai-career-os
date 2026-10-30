import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

import { stripComments } from "./copy-scan";
import { translations } from "./translations";

/**
 * Every key the browser asks for has to be in the table.
 *
 * A key that is asked for and is not there renders as *the key*: `t()`
 * returns the key itself when the table has no entry for it, so the reader
 * sees "activity.runGone" on the screen, in every language, in a place that
 * was supposed to say "This run is gone".
 *
 * Nothing else in this repository can see that:
 *
 * - The type checker cannot, because `t()` takes any string.
 * - The copy census cannot, because a key is not copy -- it is the *absence*
 *   of copy, and the census looks for words the reader sees.
 * - The table's own gate cannot, because it holds the two languages to the
 *   same key set: a key that is in neither language is in both, so it passes.
 *
 * Two of the five keys this gate found were not missing at all -- the code
 * asked for `activity.runGone` while the table carried `activity.detail.runGone`
 * -- which is the other shape of the same bug: the key and the copy are both
 * there, and they are not looking at each other.
 *
 * So the gate reads the browser's own sources, takes every literal key it
 * asks for, and holds each one against the table. The sources are the
 * population, the way the census's are: a gate that measures the wrong
 * population measures nothing.
 *
 * Only one direction is checked. The other -- a key nothing asks for -- is
 * real, and it named 187 keys the first time it ran: the navigation's own
 * labels are asked for through `item.labelKey`, the dimension names through
 * a namespace and a wire key, so a literal scan cannot see them. A gate
 * that needed 187 exceptions would train people to ignore it, and a gate
 * that cries wolf is worse than no gate: the direction that matters is the
 * one that shows a raw key on a reader's screen.
 *
 * One family is closed enough to check the other way too: the dashboard's
 * `*Description` lines are each asked for by literal name, so a description
 * with no literal reader is dead copy. Keys the block reads through a roster
 * (`RANKING_HINT_KEYS`) do not end in `Description` and stay outside it.
 */

const ROOT = fileURLToPath(new URL("../../", import.meta.url));

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

// A literal key, asked for by name. The dotted shape is the filter: a key
// has a namespace, and a call that takes a word or a path is not one.
const KEY_CALL = /\b(?:t|translate)\(\s*["`]([a-z][A-Za-z0-9]*(?:\.[A-Za-z0-9]+)+)["`]/g;

const en = new Set(keysOf(translations.en));
const zh = new Set(keysOf(translations.zh));

describe("the keys the browser asks for", () => {
  it("are all in the table, in both languages", () => {
    const missing: string[] = [];
    for (const rel of browserSources()) {
      // The comments go first: a `t("...")` in a comment is not a key the
      // browser asks for.
      const source = stripComments(readFileSync(join(ROOT, rel), "utf-8"));
      for (const m of source.matchAll(KEY_CALL)) {
        const key = m[1];
        if (!en.has(key)) missing.push(`${rel}: ${key} (not in the English table)`);
        else if (!zh.has(key)) missing.push(`${rel}: ${key} (not in the Chinese table)`);
      }
    }
    // The offenders go in the message. Without them the red reads
    // `expected [ Array(2) ] to deeply equal []`, which names neither the key nor the file,
    // and the reader has to re-run the scan by hand to find out what the gate found.
    expect(missing, `a key is asked for and the table does not answer it:\n${missing.join("\n")}`).toEqual([]);
  });
});

/** Every literal key the browser's sources ask for. */
function askedKeys(files = browserSources()): Set<string> {
  const asked = new Set<string>();
  for (const rel of files) {
    const source = stripComments(readFileSync(join(ROOT, rel), "utf-8"));
    for (const m of source.matchAll(KEY_CALL)) asked.add(m[1]);
  }
  return asked;
}

/** The dashboard's description lines that no source asks for by name. */
function unreadDashboardDescriptions(
  block: Record<string, unknown>,
  asked: Set<string>
): string[] {
  return Object.keys(block)
    .filter((key) => /Description$/.test(key))
    .map((key) => `dashboard.${key}`)
    .filter((key) => !asked.has(key));
}

describe("the dashboard's description lines", () => {
  it("are each asked for by name", () => {
    const block = translations.en.dashboard as unknown as Record<string, unknown>;
    const descriptions = Object.keys(block).filter((key) => /Description$/.test(key));
    // The family is the population: a renamed suffix or a moved block must not
    // leave the case with nothing to charge.
    expect(descriptions.length, "the scan found no description lines").toBeGreaterThan(15);
    const unread = unreadDashboardDescriptions(block, askedKeys());
    expect(
      unread,
      `dashboard descriptions no source asks for:\n${unread.join("\n")}`
    ).toEqual([]);
  });

  it("would still see a dead description, and stays out of roster-read keys", () => {
    const asked = new Set(["dashboard.liveDescription"]);
    expect(
      unreadDashboardDescriptions(
        { liveDescription: "asked for", deadDescription: "dead" },
        asked
      )
    ).toEqual(["dashboard.deadDescription"]);
    expect(
      unreadDashboardDescriptions({ skillGapsHint: "roster-read", count: 2 }, new Set())
    ).toEqual([]);
  });
});
