// One-off: regenerate the copy census's KNOWN map from the browser's sources.
// Run with `node --experimental-strip-types scripts/regen-known.mjs`; it
// rewrites the block in `src/lib/i18n/copy-census.test.ts` in place.
//
// The scan is not written here. It lives in `src/lib/i18n/copy-scan.ts`,
// next to the gate that uses it, because two copies of one rule is two
// rules -- and the moment they drifted, this script regenerated the list
// from a different population than the gate measured.
import { readFileSync, writeFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

import { everyOffender } from "../src/lib/i18n/copy-scan.ts";

const HERE = dirname(fileURLToPath(import.meta.url));
const TEST = join(HERE, "..", "src", "lib", "i18n", "copy-census.test.ts");

const found = new Map();
for (const o of everyOffender()) {
  if (!found.has(o.file)) found.set(o.file, new Set());
  found.get(o.file).add(o.value);
}

let out = "";
for (const [file, set] of [...found.entries()].sort()) {
  out += `  ${JSON.stringify(file)}: [\n`;
  for (const v of [...set].sort()) out += `    ${JSON.stringify(v)},\n`;
  out += `  ],\n`;
}

const source = readFileSync(TEST, "utf-8");
const start = source.indexOf("const KNOWN: Record<string, string[]> = {");
if (start < 0) throw new Error("the KNOWN block is not where this script expects it");
const bodyStart = source.indexOf("{", start);
const bodyEnd = source.indexOf("\n};", bodyStart);
if (bodyEnd < 0) throw new Error("the KNOWN block is not closed where this script expects it");
const rewritten =
  source.slice(0, bodyStart + 1) + "\n" + out + source.slice(bodyEnd);
writeFileSync(TEST, rewritten, "utf-8");
process.stderr.write(
  `files: ${found.size} entries: ${[...found.values()].reduce((n, s) => n + s.size, 0)}\n`
);
