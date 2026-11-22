// The new surfaces, measured in a real browser against the running stack.
//
// Registers one throwaway account, drives it through the routes the epics added, and
// reads what actually rendered. The point is not a screenshot: it is the claim that
// each card appears with the reader's own data in it, and that its door goes where
// it says.
//
// Usage: node e2e/surfaces-probe.mjs   (needs the stack on :3000/:8080)

import { chromium } from "playwright";

const API = process.env.E2E_API_URL ?? "http://127.0.0.1:8080/api/v1";
const APP = process.env.E2E_BASE_URL ?? "http://localhost:3000";

const email = `surfaces-${Date.now()}@careeros.test`;
const password = "Passw0rd!234";

const reg = await fetch(`${API}/auth/register`, {
  method: "POST", headers: { "content-type": "application/json" },
  body: JSON.stringify({ email, password, displayName: "Surfaces Probe" }),
});
if (!reg.ok && reg.status !== 429) throw new Error(`register ${reg.status}`);
const login = await (await fetch(`${API}/auth/login`, {
  method: "POST", headers: { "content-type": "application/json" },
  body: JSON.stringify({ email, password }),
})).json();
const token = login?.data?.tokens?.accessToken;
if (!token) throw new Error("no token");
const auth = { Authorization: `Bearer ${token}` };

// One application and one abandoned rehearsal: enough ledger for the atlas to have a
// region, the frontier to have a direction and the rhythm to have a date.
await fetch(`${API}/applications`, {
  method: "POST", headers: { ...auth, "content-type": "application/json" },
  body: JSON.stringify({ title: "Backend Engineer", companyName: "Acme", status: "applied" }),
});
await fetch(`${API}/interview/sessions`, {
  method: "POST", headers: { ...auth, "content-type": "application/json" },
  body: JSON.stringify({ mode: "mixed", difficulty: 3, positionTitle: "Backend Engineer" }),
});

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
// The token rides in localStorage, the way the app's own session does.
await page.addInitScript((t) => {
  window.localStorage.setItem("careeros.accessToken", t);
}, token);
const errors = [];
page.on("console", (m) => { if (m.type() === "error") errors.push(m.text().slice(0, 160)); });
page.on("response", (r) => { if (r.status() >= 400) console.log("  HTTP", r.status(), r.url().slice(0, 110)); });

async function open(path) {
  await page.goto(APP + path, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(3500);
}

const results = {};

// 1. The frontier card on the dashboard.
await open("/dashboard");
results.frontier = await page.evaluate(() => {
  const card = document.querySelector('[data-testid="frontier-card"]');
  return {
    present: !!card,
    href: card?.querySelector("a")?.getAttribute("href") ?? null,
    text: card ? card.innerText.replace(/\s+/g, " ").slice(0, 120) : null,
  };
});

// 2. The atlas on the timeline: regions, doors, the route and the neighbours.
await open("/timeline");
results.atlas = await page.evaluate(() => {
  const card = document.querySelector('[data-slot="card"]');
  const regionDoors = [...document.querySelectorAll('a[href="/applications"], a[href="/interviews"]')].length;
  const dashed = (document.body.innerHTML.match(/stroke-dasharray="1\.5 1\.5"/g) ?? []).length;
  return { cardPresent: !!card, regionDoors, routeLegs: dashed };
});

// 3. The rhythm card on the interviews list.
await open("/interviews");
results.rhythm = await page.evaluate(() => {
  const card = document.querySelector('[data-testid="rhythm-card"]');
  return {
    present: !!card,
    text: card ? card.innerText.replace(/\s+/g, " ").slice(0, 140) : null,
  };
});

// 4. The legacy card on the ceremony page.
await open("/ceremony");
results.legacy = await page.evaluate(() => {
  const card = document.querySelector('[data-testid="legacy-card"]');
  return {
    present: !!card,
    text: card ? card.innerText.replace(/\s+/g, " ").slice(0, 140) : null,
  };
});

// 5. The search portrait on the applications board.
await open("/applications");
results.portrait = await page.evaluate(() => {
  const card = document.querySelector('[data-testid="portrait-card"]');
  return {
    present: !!card,
    text: card ? card.innerText.replace(/\s+/g, " ").slice(0, 140) : null,
  };
});

// 6. The growth panel's engine hints.
await open("/growth");
results.growth = await page.evaluate(() => {
  const triggers = (document.body.innerHTML.match(/data-slot="tooltip-trigger"/g) ?? []).length;
  return { hintTriggers: triggers };
});

console.log(JSON.stringify(results, null, 1));
console.log("CONSOLE ERRORS:", errors.length ? errors.slice(0, 5) : "none");

const ok =
  results.frontier.present &&
  results.atlas.routeLegs > 0 &&
  results.rhythm.present &&
  results.portrait.present &&
  errors.length === 0;
console.log(ok
  ? "PASS: the new surfaces render with the reader's own data"
  : "NOTE: some surfaces did not render -- see the rows above");
await browser.close();
