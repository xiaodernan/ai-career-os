#!/usr/bin/env node
/**
 * Regenerate the copy census's KNOWN list.
 *
 * The gate (`frontend/src/lib/i18n/copy-census.test.ts`) refuses a hardcoded string that is
 * not on its `KNOWN` list, and tolerates a listed string that has since been fixed. So the
 * list is not checked against the scan — it is *produced* from it: run this after fixing
 * copy, paste the block it prints into the test, and delete the entries that are gone.
 *
 * It imports the same `copy-scan.ts` the gate uses, so the tool and the gate cannot measure
 * different populations. Node 24 strips the types on import; the scan has no path aliases.
 *
 *     node scripts/regen-known.mjs
 */
import { everyOffender } from "../frontend/src/lib/i18n/copy-scan.ts";

const byFile = new Map();
for (const { file, value } of everyOffender()) {
  if (!byFile.has(file)) byFile.set(file, new Set());
  byFile.get(file).add(value);
}

const files = [...byFile.keys()].sort();
const total = [...byFile.values()].reduce((n, values) => n + values.size, 0);

const lines = ["const KNOWN: Record<string, string[]> = {"];
for (const file of files) {
  lines.push(`  ${JSON.stringify(file)}: [`);
  for (const value of [...byFile.get(file)].sort()) {
    lines.push(`    ${JSON.stringify(value)},`);
  }
  lines.push("  ],");
}
lines.push("};");

// The block goes to stdout so it can be redirected into a file; the tally goes to stderr so
// it does not end up inside the pasted literal.
console.log(lines.join("\n"));
console.error(`${total} strings in ${files.length} files`);
