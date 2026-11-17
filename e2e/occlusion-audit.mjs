// Occlusion audit — is any interactive element invisible to the pointer because another element sits on it?
// elementFromPoint skips pointer-events:none hit areas, so any foreign element on top means a real block.

import { chromium } from "playwright";
import process from "node:process";

// No origin default is asserted by the file — pass the endpoint in, or the script refuses.
const API = process.env.E2E_API_URL;
const APP = process.env.E2E_BASE_URL;
if (!API || !APP) throw new Error("pass E2E_API_URL and E2E_BASE_URL (this file asserts no origin of its own)");
const email = `occlude-${Date.now()}@careeros.test`;
const password = "Passw0rd!234";

async function main() {
  const reg = await fetch(`${API}/auth/register`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ email, password, displayName: "Occlusion Audit" }),
  });
  if (!reg.ok) throw new Error(`register ${reg.status}`);

  const browser = await chromium.launch();
  const context = await browser.newContext({
    baseURL: APP, viewport: { width: 1440, height: 900 }, locale: "en-US", reducedMotion: "reduce",
  });
  const page = await context.newPage();

  await page.goto("/login", { waitUntil: "networkidle" });
  await page.locator("#email").fill(email);
  await page.locator("#password").fill(password);
  await page.locator('button[type="submit"]').click();
  await page.waitForURL((url) => !url.pathname.includes("/login"), { timeout: 30_000 });

  const audit = `(() => {
    const hits = [];
    const interactives = document.querySelectorAll('a,button,input,select,textarea,[role="button"]');
    for (const el of interactives) {
      const cs = getComputedStyle(el);
      if (cs.visibility === "hidden" || cs.display === "none" || cs.pointerEvents === "none") continue;
      const r = el.getBoundingClientRect();
      if (r.width < 2 || r.height < 2) continue;
      if (r.bottom < 0 || r.right < 0 || r.top > window.innerHeight || r.left > window.innerWidth) continue;
      const cx = Math.max(1, Math.min(window.innerWidth - 1, r.left + r.width / 2));
      const cy = Math.max(1, Math.min(window.innerHeight - 1, r.top + r.height / 2));
      const hit = document.elementFromPoint(cx, cy);
      if (hit && hit !== el && !el.contains(hit) && !hit.contains(el)) {
        const desc = (n) => {
          const cls = typeof n.className === "string" ? n.className.trim().split(/\\s+/).slice(0, 3).join(".") : "";
          return n.tagName.toLowerCase() + (cls ? "." + cls : "");
        };
        hits.push({ target: desc(el), hitBy: desc(hit) });
        if (hits.length >= 10) break;
      }
    }
    return hits;
  })()`;

  const routes = ["/dashboard","/jobs","/applications","/resumes","/interviews","/copilot","/knowledge","/activity","/notifications","/networking","/offers","/replies","/growth","/studio","/ceremony","/letters","/settings","/playbook","/tour","/admin"];
  for (const route of routes) {
    try {
      await page.goto(route, { waitUntil: "load", timeout: 90_000 });
      if (route === "/admin") {
        try { await page.locator("#admin-pass").fill("123", { timeout: 5_000 }); await page.locator('button[type="submit"]').click(); await page.waitForTimeout(1_000); } catch {}
      }
      await page.waitForTimeout(400);
      const hits = await page.evaluate(audit);
      console.log(`${route.padEnd(14)} occluded=${hits.length}${hits.length ? " :: " + hits.map((h) => h.target + " < " + h.hitBy).join(" | ") : ""}`);
    } catch (error) {
      console.log(`${route.padEnd(14)} ERROR ${error instanceof Error ? error.message.split("\n")[0] : error}`);
    }
  }
  await browser.close();
}
main().catch((e) => { console.error(e); process.exit(1); });
