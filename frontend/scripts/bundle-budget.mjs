/**
 * The bundle budget gate (Epic 127).
 *
 * `next build` prints a "First Load JS" table, but nothing makes a contributor
 * read it -- a route that silently grew 100 kB shows up as a slower product,
 * not as a red X. This script recomputes the per-route first-load weight the
 * way the table does (the minified chunks the app-build-manifest names for
 * the route, gzip-compressed, because that is the bytes a proxy transmits),
 * and fails when any route exceeds its budget.
 *
 * Budget: every page route stays under 340 kB gzip. Measured landscape at
 * adoption (2026-11-11, next build on this host): the heaviest route
 * (/applications) is ~301 kB gzip, the shared base is ~103 kB, so the budget
 * names a breach rather than a bother. Tighten this, never raise it without
 * writing why in the commit.
 *
 * Usage:  npm run budget        (runs `next build` first)
 *         node scripts/bundle-budget.mjs
 */
import { readFileSync, existsSync } from "node:fs";
import { gzipSync } from "node:zlib";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const MANIFEST = join(ROOT, ".next", "app-build-manifest.json");
const BUDGET_KIB = 340;

if (!existsSync(MANIFEST)) {
  console.error("bundle-budget: no .next/app-build-manifest.json -- run `next build` first (or `npm run budget`)");
  process.exit(2);
}

const manifest = JSON.parse(readFileSync(MANIFEST, "utf8"));
const pages = manifest.pages ?? {};

const rows = [];
const gzipCache = new Map();
const gzipOf = (chunk) => {
  if (!gzipCache.has(chunk)) {
    const path = join(ROOT, ".next", chunk);
    gzipCache.set(chunk, existsSync(path) ? gzipSync(readFileSync(path)).length : 0);
  }
  return gzipCache.get(chunk);
};

for (const [route, chunks] of Object.entries(pages)) {
  if (!route.endsWith("/page") && route !== "/page") continue;
  const unique = [...new Set(chunks)];
  const bytes = unique.reduce((sum, chunk) => sum + gzipOf(chunk), 0);
  rows.push({ route, bytes });
}

rows.sort((a, b) => b.bytes - a.bytes);
const offenders = rows.filter(({ bytes }) => bytes > BUDGET_KIB * 1024);

console.log("bundle-budget: per-route first-load JS (gzip, this host's build)");
for (const { route, bytes } of rows) {
  const kib = (bytes / 1024).toFixed(1);
  const flag = bytes > BUDGET_KIB * 1024 ? "  OVER BUDGET" : "";
  console.log(`${String(kib).padStart(7)} kB  ${route}${flag}`);
}
console.log(`\n${rows.length} page routes measured; budget ${BUDGET_KIB} kB gzip each.`);

if (offenders.length > 0) {
  console.error(
    `\nbundle-budget: ${offenders.length} route(s) over budget. Either shrink what the route ships ` +
    `(dynamic import, lazy boundary, fewer icons) or move the budget -- and the move needs a reason in the commit.`
  );
  process.exit(1);
}
console.log("bundle-budget: OK");
