// Visual sweep — capture every main surface in one session so nobody has to
// click through by hand. Registers a throwaway account via the real API,
// logs in, and screenshots each route. The images are the review artifact;
// they land in e2e/test-results/visual-sweep/ (gitignored).
//
// Usage: node e2e/visual-sweep.mjs

import { chromium } from "playwright";
import { mkdirSync, writeFileSync } from "node:fs";
import path from "node:path";
import process from "node:process";

const API = process.env.E2E_API_URL ?? "http://127.0.0.1:8080/api/v1";
const APP = process.env.E2E_BASE_URL ?? "http://localhost:3000";
const OUT = path.join("test-results", "visual-sweep");

const email = `sweep-${Date.now()}@careeros.test`;
const password = "Passw0rd!234";
const displayName = "Visual Sweep";

const log = (s) => console.log(s);

async function main() {
  const register = await fetch(`${API}/auth/register`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ email, password, displayName }),
  });
  if (!register.ok && register.status !== 429) {
    const text = await register.text();
    throw new Error(`register failed: HTTP ${register.status} ${text.slice(0, 200)}`);
  }
  log(`account: ${email}`);

  // pick a job id for the detail page, via the API token we just earned
  const loginRes = await fetch(`${API}/auth/login`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  const loginJson = await loginRes.json();
  const accessToken = loginJson?.data?.tokens?.accessToken;
  if (!accessToken) throw new Error(`login did not return an access token: ${JSON.stringify(loginJson).slice(0, 300)}`);

  const jobsRes = await fetch(`${API}/jobs?limit=1`, {
    headers: { authorization: `Bearer ${accessToken}` },
  });
  const jobsJson = await jobsRes.json();
  const firstJobId =
    jobsJson?.data?.items?.[0]?.id ?? jobsJson?.data?.[0]?.id ?? null;
  log(`job detail target: ${firstJobId}`);

  mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch();
  const context = await browser.newContext({
    baseURL: APP,
    viewport: { width: 1440, height: 900 },
    locale: "en-US",
    reducedMotion: "reduce",
  });
  const page = await context.newPage();
  page.on("pageerror", (error) => console.log(`[pageerror] ${error.message}`));

  // Log in through the real form so every authed capture is honest.
  await page.goto("/login", { waitUntil: "networkidle" });
  try {
    await page.locator("#email").fill(email, { timeout: 8_000 });
    await page.locator("#password").fill(password);
    await page.locator('button[type="submit"]').click();
  } catch {
    await page.getByLabel(/email/i).first().fill(email);
    await page.getByLabel(/password/i).first().fill(password);
    await page.getByRole("button", { name: /sign|continue|登录|继续|注册/i }).first().click();
  }
  await page.waitForURL((url) => !url.pathname.includes("/login"), { timeout: 30_000 });
  log(`landed on ${page.url()}`);

  const stops = [
    ["dashboard", "/dashboard"],
    ["jobs", "/jobs"],
    ...(firstJobId ? [["job-detail", `/jobs/${firstJobId}`]] : []),
    ["applications", "/applications"],
    ["resumes", "/resumes"],
    ["interviews", "/interviews"],
    ["copilot", "/copilot"],
    ["knowledge", "/knowledge"],
    ["activity", "/activity"],
    ["notifications", "/notifications"],
    ["networking", "/networking"],
    ["offers", "/offers"],
    ["replies", "/replies"],
    ["growth", "/growth"],
    ["studio", "/studio"],
    ["ceremony", "/ceremony"],
    ["letters", "/letters"],
    ["settings", "/settings"],
    ["playbook", "/playbook"],
    ["tour", "/tour"],
    ["admin", "/admin"],
  ];

  for (const [name, route] of stops) {
    try {
      await page.goto(route, { waitUntil: "networkidle", timeout: 30_000 });
      if (route === "/admin") {
        try {
          await page.locator("#admin-pass").fill("123", { timeout: 5_000 });
          await page.locator('button[type="submit"]').click();
          await page.waitForTimeout(1_000);
        } catch {
          // leave the locked door as the capture — that is also the truth
        }
      }
      await page.waitForTimeout(600);
      const file = path.join(OUT, `${name}.png`);
      await page.screenshot({ path: file });
      log(`shot ${name} -> ${file}`);
    } catch (error) {
      log(`MISS ${name}: ${error instanceof Error ? error.message.split("\n")[0] : String(error)}`);
    }
  }

  // and the landing page, fresh, signed out
  const guest = await browser.newContext({ baseURL: APP, viewport: { width: 1440, height: 900 }, locale: "en-US" });
  const guestPage = await guest.newPage();
  await guestPage.goto("/", { waitUntil: "networkidle" });
  await guestPage.screenshot({ path: path.join(OUT, "landing.png") });
  log("shot landing ->" + path.join(OUT, "landing.png"));
  await guest.close();

  writeFileSync(
    path.join(OUT, "account.txt"),
    `${email}\n${password}\n${accessToken.slice(0, 12)}...\n`
  );

  await browser.close();
  log("done");
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
