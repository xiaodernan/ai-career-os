// One-off diagnostic: ask the running backend for every route the frontend's
// endpoint map names, and report the ones it does not answer.
//
// The point is the 404s: a route the client names and the server does not
// route is a screen that silently does nothing, and the client is written
// to fall back when a route is missing, so it looks like a design choice
// rather than a gap.
//
// The probe gives the account a parsed resume first, because the engines
// that read the profile answer 404 for a user with no resume -- which is
// the honest answer, and not a missing route. A census that registers that
// as a gap is measuring the wrong thing.
//
//   node scripts/probe-endpoints.mjs            # against localhost:8080
//   API=http://host:port/api/v1 node scripts/probe-endpoints.mjs
import { readFileSync } from "node:fs";

const API = process.env.API ?? "http://127.0.0.1:8080/api/v1";
const FRONTEND = "D:/求职平台/frontend/src/lib/api/endpoints.ts";

const source = readFileSync(FRONTEND, "utf-8");
const body = source.slice(source.indexOf("export const endpoints"));
const paths = new Set();
for (const m of body.matchAll(/"(\/[a-z0-9\-\/{}]*)"/gi)) {
  paths.add(m[1].replace(/\$\{[^}]+\}/g, "probe"));
}
for (const m of body.matchAll(/`(\/[^`]*)`/g)) {
  paths.add(m[1].replace(/\$\{[^}]+\}/g, "probe"));
}

// The user.
const email = `probe${Date.now().toString(36)}@careeros.test`;
const reg = await fetch(`${API}/auth/register`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ email, password: "Passw0rd!234", displayName: "Probe" }),
});
if (!reg.ok) {
  console.log("register failed", reg.status, await reg.text());
  process.exit(1);
}
const { data } = await reg.json();
const auth = { Authorization: `Bearer ${data.tokens.accessToken}` };

// A workspace with a parsed resume.
//
// The engines that read the profile (the story bank, the role
// suggestions) answer 404 for a user with no resume -- which is the
// honest answer, and not a missing route. A census that registers that
// as a gap is measuring the wrong thing, so the probe gives the account
// a resume first.
const resume = await fetch(`${API}/resumes`, {
  method: "POST",
  headers: { ...auth, "Content-Type": "application/json" },
  body: JSON.stringify({
    title: "Probe Resume",
    plaintext:
      "Backend engineer with six years of Java and Spring. Built payment " +
      "services at scale, cut p99 latency by 40%. Led a team of four.",
  }),
});
const { data: resumeData } = await resume.json();
await fetch(`${API}/resumes/${resumeData.id}/parse`, {
  method: "POST",
  headers: { ...auth, "Content-Type": "application/json" },
  body: "{}",
});

const rows = [];
for (const path of [...paths].sort()) {
  for (const method of ["GET", "POST"]) {
    const res = await fetch(`${API}${path}`, {
      method,
      headers: { ...auth, "Content-Type": "application/json" },
      body: method === "POST" ? "{}" : undefined,
    });
    await res.text();
    if (res.status === 404 || res.status === 405) {
      rows.push(`${method} ${path} -> ${res.status}`);
    }
  }
}
console.log(rows.length ? rows.join("\n") : "every endpoint answered something other than 404/405");
console.log(`checked ${paths.size} paths`);
