// One-off: regenerate the copy census's KNOWN map from the browser's sources.
// Run with `node scripts/regen-known.mjs`; it rewrites the block in
// `src/lib/i18n/copy-census.test.ts` in place.
import { readFileSync, readdirSync, statSync, writeFileSync } from "node:fs";
import { join, relative, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, "..", "src");
const TEST = join(ROOT, "lib", "i18n", "copy-census.test.ts");

const COPY_ATTRIBUTES = [
  "title",
  "description",
  "label",
  "placeholder",
  "aria-label",
  "confirmLabel",
  "ctaLabel",
  "alt",
];

function browserSources() {
  const out = [];
  const walk = (dir) => {
    for (const entry of readdirSync(dir)) {
      const full = join(dir, entry);
      if (statSync(full).isDirectory()) {
        walk(full);
        continue;
      }
      if (!entry.endsWith(".tsx")) continue;
      if (entry.includes(".test.")) continue;
      out.push(relative(ROOT, full).replace(/\\/g, "/"));
    }
  };
  walk(join(ROOT, "app"));
  walk(join(ROOT, "components"));
  return out.sort();
}

const found = new Map();
const add = (file, value) => {
  if (!found.has(file)) found.set(file, new Set());
  found.get(file).add(value);
};

const attrPattern = new RegExp(`\\b(${COPY_ATTRIBUTES.join("|")})="([^"\\n]+)"`, "g");
const textPattern = /(?:>|\})([^<>{}]{1,80}?)(?=<|\{)/g;

const NOT_COPY = new Set(["Career", "CareerOS", "OS"]);

for (const rel of browserSources()) {
  const text = readFileSync(join(ROOT, rel), "utf-8");
  for (const m of text.matchAll(attrPattern)) {
    const value = m[2];
    if (!/^[A-Z]/.test(value)) continue;
    add(rel, value);
  }
  for (const m of text.matchAll(textPattern)) {
    const value = m[1].trim();
    if (!value) continue;
    if (!/^[A-Z][a-z]/.test(value)) continue;
    if (/[(){};=<>|]/.test(value)) continue;
    if (/^&[a-z]+;/.test(value)) continue;
    if (NOT_COPY.has(value)) continue;
    add(rel, value);
  }
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

