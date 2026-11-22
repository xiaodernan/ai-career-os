// 369: the frontier card, measured in a real browser.
//
// Registers a throwaway account, starts a rehearsal and walks away from it (never
// answers), then opens the dashboard and reads what the card says. The claim is
// that a rehearsal left half-done is the direction the world points -- and that a
// reader with nothing waiting sees no card at all rather than an invented errand.
//
// Usage: node e2e/frontier-probe.mjs   (needs the stack on :3000/:8080)

import { chromium } from "playwright";

const API = process.env.E2E_API_URL ?? "http://127.0.0.1:8080/api/v1";
const APP = process.env.E2E_BASE_URL ?? "http://localhost:3000";

const email = `frontier-${Date.now()}@careeros.test`;
const password = "Passw0rd!234";

const reg = await fetch(`${API}/auth/register`, {
  method: "POST", headers: { "content-type": "application/json" },
  body: JSON.stringify({ email, password, displayName: "Frontier Probe" }),
});
if (!reg.ok && reg.status !== 429) throw new Error(`register ${reg.status}`);
const login = await (await fetch(`${API}/auth/login`, {
  method: "POST", headers: { "content-type": "application/json" },
  body: JSON.stringify({ email, password }),
})).json();
const token = login?.data?.tokens?.accessToken;
if (!token) throw new Error("no token");
const auth = { Authorization: `Bearer ${token}` };

// One rehearsal, started and abandoned: the opening question is asked and never
// answered, which is exactly the state the rule ranks highest.
const started = await fetch(`${API}/interview/sessions`, {
  method: "POST", headers: { ...auth, "content-type": "application/json" },
  body: JSON.stringify({ mode: "mixed", difficulty: 3, positionTitle: "Backend Engineer" }),
});
const session = started.ok ? (await started.json())?.data : null;
console.log("rehearsal started:", started.status, session?.id ? "yes" : "no");

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
await page.addInitScript((t) => {
  window.localStorage.setItem("careeros.accessToken", t);
}, token);
page.on("response", (r) => {
  if (r.url().includes("/api/v1/")) console.log("  NET", r.status(), r.url().replace(/^.*\/api\/v1/, "/api/v1").slice(0, 50));
});
page.on("console", (m) => { if (m.type() === "error") console.log("  CONSOLE", m.text().slice(0, 200)); });
await page.goto(APP + "/dashboard", { waitUntil: "domcontentloaded" });
await page.waitForTimeout(8000);

const seen = await page.evaluate(() => {
  const card = document.querySelector('[data-testid="frontier-card"]');
  return {
    present: !!card,
    text: card ? card.innerText.replace(/\s+/g, " ").slice(0, 300) : null,
    href: card?.querySelector("a")?.getAttribute("href") ?? null,
  };
});
console.log("FRONTIER:", JSON.stringify(seen, null, 1));
const diag = await page.evaluate(() => ({
  url: location.pathname,
  body: document.body.innerText.slice(0, 200),
  cards: [...document.querySelectorAll('[data-testid]')].map(e => e.getAttribute('data-testid')),
}));
console.log("DIAG", JSON.stringify(diag, null, 1));
const sess = await (await fetch(`${API.replace('/api/v1','')}/api/v1/interview/sessions`, { headers: auth })).json();
console.log("SESSIONS:", JSON.stringify((sess?.data?.items ?? sess?.data ?? []).slice(0,3).map(s => ({id: s.id, status: s.status})), null, 1));

const ok = seen.present && seen.href === "/interviews"
  && /rehearsal/i.test(seen.text ?? "");
console.log(ok
  ? "PASS: an abandoned rehearsal is the direction the world points"
  : "FAIL: the frontier card did not name the open rehearsal");
process.exitCode = ok ? 0 : 1;
await browser.close();
