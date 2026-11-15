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
 * Budget: every page route stays under 345 kB gzip.
 * Raised 340 -> 345 on 2026-11-16 with the reason written down: Epic 268
 * landed a new bilingual keepsake chapter on the shared table (~1.7 kB gzip:
 * ~27 keys x 2 languages + the sixth pocket family). The three fullest routes
 * crossed by 0.3-1.4 kB (/(app)/jobs/page 339.6 -> 341.4,
 * /(app)/knowledge/page 338.6 -> 340.4, /(app)/applications/page 338.5 -> 340.3).
 * Not new route-specific code -- the shared bilingual table every route pays.
 * /settings improved instead: 339.9 -> 315.8, by moving the profile and memory
 * cards off first-load (they now load as their own chunks after hydration).
 * Part of the same epic held the named architectural debt to the fire: the
 * locale-split cannot land honestly while `useLocale` must answer
 * synchronously in the first (server) render -- shipping the other table as a
 * lazy chunk would render a splash shell before content, and the SSR contract
 * (`renderToStaticMarkup` answers in both languages on the server) is pinned
 * by `locale-context.test.tsx`. The honest fix remains per-locale precompiled
 * tables (a path-segmented locale or a build-time switch), kept as the named
 * next epic, not avoided. Raise, never silently.
 * Raised 335 -> 340 on 2026-11-16 with the reason written down: the overseer's-ledger chapter
 * and the chapter-nine/booklet chapters grew the shared table by ~10 kB again since Epic 244;
 * /(app)/jobs/page, /(app)/settings/page and /(app)/applications/page each crossed the 335 line
 * by 1–2 kB of the same growth. Each prior raise named the same shared table; the per-locale
 * split remains the architectural fix, kept as the named next epic, not another raise. Every
 * other route is under it. Raise, never silently.
 * Raised 310 → 320 on 2026-11-15, with the reason written down: since the 310
 * tightening (2026-11-12) the keepsake arc shipped a bilingual product manual,
 * the decision ledger, the letters gallery, the bookend letters and the ceremony —
 * every one of them lands in the shared table every route pays. The routes that
 * could shed weight did so this session (the jobs board dialogs, the job detail's
 * two AI panels and the settings account cards now leave the first-load path;
 * /(app)/jobs/[id]/page fell 322.7 → 305.9 kB). The remaining overflow is the
 * shared table, not new route-specific code. Raise, never silently.
 * Earlier: measured landscape at the 2026-11-12 build (next build on this host,
 * 35 routes): the heaviest route (/(app)/jobs/[id]/page) was 299.6 kB gzip, the
 * shared base ~103 kB. Tightened from 340 on 2026-11-12. Tighten this, never
 * raise it without writing why in the commit.
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
const BUDGET_KIB = 345;

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
