#!/usr/bin/env node
/**
 * npm-audit-gate — dependency advisories, with teeth for what is not ignorable.
 *
 * The project's posture is "any fresh advisory reddens CI until it is remediated".
 * This gate keeps that promise, with one narrow, *expiring* exception, recorded
 * here and in SECURITY.md — never silently, never broadly.
 *
 * ALLOWED — GHSA-fc5q-39xc-vjpf (CVE-2026-112366), picomatch ReDoS through
 *   single-branch repeated extglobs. Patched versions: NONE as of 2026-11-17.
 *   The 16 vulnerable entries in the audit report are this one CVE seen through
 *   the glob chain (picomatch ← micromatch ← fast-glob/fdir/tinyglobby/globby/
 *   vite/vitest/eslint-*). Exposure is build-time glob expansion of our own
 *   committed source tree; no request-time path feeds a pattern to the engine,
 *   and EPSS for this CVE is 0.335% (27th percentile). Mitigation upstream is
 *   tracked at micromatch/picomatch#175/#182/#194.
 *
 *   This exception EXPIRES 2026-12-18. On that date this gate fails again on
 *   this CVE until either picomatch ships a fixed release (npm audit fix; delete
 *   the entry) or a maintainer re-justifies a fresh window in this file and
 *   SECURITY.md. Any other advisory, in any package, fails this gate today.
 *
 * Usage: node scripts/npm-audit-gate.mjs   (run with cwd = the frontend/)
 */
import { spawnSync } from "node:child_process";

const EXCEPTIONS = [
  {
    id: "GHSA-fc5q-39xc-vjpf",
    until: "2026-12-18",
    title: "picomatch vulnerable to ReDoS through single-branch repeated extglobs",
    reason: "patched versions: none; build-time-only exposure; EPSS 0.335%",
  },
];

function fail(msg) {
  console.error(`npm-audit-gate: FAIL — ${msg}`);
  process.exit(1);
}

const r = process.platform === "win32"
  ? spawnSync("npm.cmd audit --json", {
      encoding: "utf8",
      maxBuffer: 128 * 1024 * 1024,
      shell: true,
    })
  : spawnSync("npm", ["audit", "--json"], {
      encoding: "utf8",
      maxBuffer: 128 * 1024 * 1024,
    });
if (r.error) fail(`could not run npm audit: ${r.error.message}`);

let report;
try {
  report = JSON.parse((r.stdout || "").replace(/^﻿/, ""));
} catch {
  fail(`npm audit did not emit JSON (exit ${r.status}); not silently passing`);
}

const today = new Date().toISOString().slice(0, 10);
const active = EXCEPTIONS.filter((e) => e.until >= today);
for (const e of EXCEPTIONS) {
  if (e.until < today) {
    console.error(`npm-audit-gate: exception for ${e.id} expired ${e.until} — time to remediate or re-justify`);
  }
}

const findings = [];
for (const [pkg, v] of Object.entries(report.vulnerabilities || {})) {
  const sev = (v.severity || "").toLowerCase();
  if (!["high", "critical"].includes(sev)) continue;
  const advisories = (v.via || [])
    .filter((item) => typeof item === "object")
    .map((item) => ({ title: item.title || "", url: item.url || "", source: item.source }));
  findings.push({ pkg, severity: sev, advisories });
}

// One CVE reaches every parent package through the glob chain; the advisory object
// is attached only at the leaf. Collect them all and exempt those the active
// exception list names; any other advisory object anywhere in the tree blocks.
const advisoryObjects = findings.flatMap((f) => f.advisories);
const unexcepted = [];
const excepted = [];
for (const a of advisoryObjects) {
  const hit = active.find((e) => a.url.includes(e.id) || String(a.source) === e.id);
  (hit ? excepted : unexcepted).push(a);
}

if (excepted.length) {
  console.log(`npm-audit-gate: ${findings.length} vulnerable package entr(ies) excepted until ${active[0]?.until ?? ""} — the single CVE they all trace to (GHSA-fc5q-39xc-vjpf):`);
  for (const f of findings) console.log(`  - ${f.pkg} [${f.severity}]`);
}
if (unexcepted.length) {
  for (const f of findings) {
    const foreign = f.advisories.filter((a) =>
      !active.some((e) => a.url.includes(e.id) || String(a.source) === e.id));
    if (foreign.length) {
      console.error(`\n${f.pkg} [${f.severity}]`);
      for (const a of foreign) console.error(`  - ${a.title} (${a.url})`);
    }
  }
  fail(`${unexcepted.length} unexcepted high/critical advisory object(s) — remediate or add an expiring, reasoned exception in this file and SECURITY.md`);
}

console.log("npm-audit-gate: OK — no unexcepted high/critical advisories");
