import { describe, expect, it } from "vitest";
import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

/**
 * Every anchor that opens something outside this app is a place where a value the reader,
 * a model or a crawler wrote becomes a destination for a click. `safeHref` is the only
 * answer, so the gate is that no such anchor exists without it -- and because an absence
 * claim is worth nothing when the scan finds nothing, the same reader is aimed at planted
 * fixtures below, one guarded and one not, whose two verdicts must both come out right.
 */

// Stripped because fileURLToPath keeps the trailing separator on Windows, and the
// relative name below is cut at it.
const SRC = fileURLToPath(new URL("../", import.meta.url)).replace(/[\\/]+$/, "");

/** The seven files that ship a new-tab anchor, named so a renamed one is visible rather than silently gone. */
const CARRIERS = [
  "app/(app)/companies/page.tsx",
  "app/(app)/companies/[id]/page.tsx",
  "app/(app)/interviews/[id]/report/page.tsx",
  "app/(app)/jobs/[id]/page.tsx",
  "app/(app)/resumes/[id]/page.tsx",
  "components/ai/streaming-text.tsx",
  // The nightly history's run link (20.1): the record's `runUrl` was written by the job, so
  // it is a value this app did not build and the anchor takes it through `safeHref`.
  "components/monitoring/nightly-history.tsx",
];

interface AnchorRow {
  file: string;
  expr: string;
  guarded: boolean;
}

function componentFiles(dir: string, out: string[] = []): string[] {
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) componentFiles(path, out);
    else if (entry.isFile() && path.endsWith(".tsx") && !/\.(test|spec)\.tsx$/.test(path)) out.push(path);
  }
  return out;
}

/** The attribute text of the element opened at `from`, up to its first depth-0 `>`. */
function propsOf(text: string, from: number): string | null {
  let depth = 0;
  let quote = "";
  for (let i = from + 2; i < text.length; i += 1) {
    const ch = text[i];
    if (quote) {
      if (ch === quote) quote = "";
      continue;
    }
    if (ch === `"` || ch === "'") quote = ch;
    else if (ch === "{") depth += 1;
    else if (ch === "}") depth -= 1;
    else if (ch === ">" && depth === 0) return text.slice(from, i);
  }
  return null;
}

/** The expression inside `href={...}`, brace-balanced so a template literal stays whole. */
function hrefExprOf(props: string): string | null {
  const at = props.indexOf("href={");
  if (at < 0) return null;
  let depth = 0;
  for (let i = at + "href=".length; i < props.length; i += 1) {
    if (props[i] === "{") depth += 1;
    else if (props[i] === "}") {
      depth -= 1;
      if (depth === 0) return props.slice(at + "href={".length, i);
    }
  }
  return null;
}

function readAnchors(path: string, text: string): AnchorRow[] {
  const guardedNames = new Set(
    [...text.matchAll(/const\s+([A-Za-z0-9_$]+)\s*=\s*safeHref\(/g)].map((m) => m[1])
  );
  const rows: AnchorRow[] = [];
  for (const match of text.matchAll(/<a(?=[\s>])/g)) {
    const props = propsOf(text, match.index as number);
    if (!props || !props.includes(`target="_blank"`)) continue;
    const expr = hrefExprOf(props);
    if (expr === null) continue;
    const trimmed = expr.trim();
    rows.push({
      file: path.slice(SRC.length + 1).replace(/\\/g, "/"),
      expr: trimmed,
      guarded:
        trimmed.startsWith("safeHref(") || /^[A-Za-z0-9_$]+$/.test(trimmed) && guardedNames.has(trimmed),
    });
  }
  return rows;
}

const rows = componentFiles(SRC).flatMap((path) => readAnchors(path, readFileSync(path, "utf8")));

describe("anchors that leave the app", () => {
  it("finds the shipped sinks, so the gate is not reading an empty room", () => {
    // Seven named files, and two of them carry a second anchor -- that is the shipped floor.
    expect(rows.length, `found ${rows.length} new-tab anchors; expected at least ${CARRIERS.length + 2}`).toBeGreaterThanOrEqual(
      CARRIERS.length + 2
    );
    const seen = new Set(rows.map((row) => row.file));
    for (const carrier of CARRIERS) {
      expect(seen.has(carrier), `the scanner never reached ${carrier}`).toBe(true);
    }
  });

  it("holds no anchor whose href was never asked whether it opens a page", () => {
    const offenders = rows.filter((row) => !row.guarded).map((row) => `${row.file} href={${row.expr}}`);
    expect(offenders, `unguarded href at ${offenders.length} sink(s): ${offenders.join(", ")}`).toEqual([]);
  });

  it("grades a planted offense and a planted guard, so both verdicts are earned", () => {
    const planted = (href: string, decl = "") =>
      readAnchors(
        `${SRC}planted/Room.tsx`,
        `export function Room({ site }: { site: string }) {\n  ${decl}return (\n    ${href}\n  );\n}\n`
      );
    const open = planted(`<a href={site} target="_blank">go</a>`);
    expect(open.length).toBe(1);
    expect(open[0].guarded, "an ungardened href was read as safe").toBe(false);

    const inline = planted(`<a href={safeHref(site)} target="_blank">go</a>`);
    expect(inline[0].guarded, "the inline guard was not recognised").toBe(true);

    const named = planted(`<a href={url} target="_blank">go</a>`, "const url = safeHref(site);\n  ");
    expect(named[0].guarded, "a href from a guarded const was not recognised").toBe(true);

    // An anchor that stays inside the app is not a destination and is not charged here.
    expect(planted(`<a href={site}>go</a>`).length, "an in-app anchor was counted").toBe(0);
  });
});
