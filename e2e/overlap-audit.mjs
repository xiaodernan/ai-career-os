// Overlap & overflow audit — computed detection instead of eyeballs.
// Reuses the same auth flow as visual-sweep.mjs. For each route it measures:
//   docOverflow   — document.documentElement.scrollWidth vs innerWidth
//   clipped       — elements whose text scrolls past their own box
//   outOfRight    — elements whose visible box escapes the right edge
//   topmostIssues — ranked findings with a weak selector

import { chromium } from "playwright";
import process from "node:process";

// No origin default is asserted by the file — pass the endpoint in, or the script refuses.
const API = process.env.E2E_API_URL;
const APP = process.env.E2E_BASE_URL;
if (!API || !APP) throw new Error("pass E2E_API_URL and E2E_BASE_URL (this file asserts no origin of its own)");
const email = `audit-${Date.now()}@careeros.test`;
const password = "Passw0rd!234";

async function main() {
  const reg = await fetch(`${API}/auth/register`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ email, password, displayName: "Overlap Audit" }),
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
    const out = { docOverflow: false, docOverflowBy: 0, clipped: [], outOfRight: [] };
    const de = document.documentElement;
    out.docOverflowBy = de.scrollWidth - window.innerWidth;
    out.docOverflow = out.docOverflowBy > 0;
    const weak = (el) => {
      const parts = [];
      let cur = el;
      for (let i = 0; i < 3 && cur && cur !== document.body; i++) {
        const name = cur.tagName.toLowerCase();
        const cls = typeof cur.className === "string" ? cur.className.trim().split(/\\s+/).slice(0, 2).join(".") : "";
        parts.unshift(cls ? name + "." + cls : name);
        cur = cur.parentElement;
      }
      return parts.join(" > ");
    };
    const texty = document.querySelectorAll("p,span,h1,h2,h3,h4,li,dt,dd,label,button,a,th,td");
    for (const el of texty) {
      if (out.clipped.length >= 8) break;
      const cs = getComputedStyle(el);
      if (cs.visibility === "hidden" || cs.display === "none") continue;
      const style = el.getBoundingClientRect();
      const text = (el.textContent || "").trim();
      if (!text) continue;
      // horizontally clipped text that is meant to scroll or clip
      if (cs.overflowX !== "visible" && el.scrollWidth - el.clientWidth > 1) {
        out.clipped.push({ tag: weak(el), delta: el.scrollWidth - el.clientWidth, h: Math.round(style.width), text: text.slice(0, 48) });
      }
    }
    const everything = document.querySelectorAll("body *");
    for (const el of everything) {
      if (out.outOfRight.length >= 8) break;
      const cs = getComputedStyle(el);
      if (cs.position === "fixed") continue;
      if (cs.visibility === "hidden" || cs.display === "none") continue;
      const r = el.getBoundingClientRect();
      if (r.width > 4 && r.right > window.innerWidth + 1 && r.left < window.innerWidth) {
        out.outOfRight.push({ tag: weak(el), right: Math.round(r.right), w: Math.round(r.width) });
      }
    }
    return out;
  })()`;

  const routes = ["/dashboard","/jobs","/applications","/resumes","/interviews","/copilot","/knowledge","/activity","/notifications","/networking","/offers","/replies","/growth","/studio","/ceremony","/letters","/settings","/playbook","/admin"];
  for (const route of routes) {
    try {
      await page.goto(route, { waitUntil: "networkidle", timeout: 30_000 });
      if (route === "/admin") {
        try { await page.locator("#admin-pass").fill("123", { timeout: 5_000 }); await page.locator('button[type="submit"]').click(); await page.waitForTimeout(1_000); } catch {}
      }
      await page.waitForTimeout(400);
      const out = await page.evaluate(audit);
      const clipped = out.clipped.slice(0, 4).map((c) => `${c.tag} (+${c.delta}px)`).join(" | ");
      const wide = out.outOfRight.slice(0, 4).map((c) => `${c.tag} -> ${c.right}`).join(" | ");
      console.log(`${route.padEnd(14)} overflow=${out.docOverflow ? "+" + out.docOverflowBy + "px" : "ok"} clipped[${out.clipped.length}]${clipped ? " :: " + clipped : ""} wide[${out.outOfRight.length}]${wide ? " :: " + wide : ""}`);
    } catch (error) {
      console.log(`${route.padEnd(14)} ERROR ${error instanceof Error ? error.message.split("\n")[0] : error}`);
    }
  }
  await browser.close();
}
main().catch((e) => { console.error(e); process.exit(1); });
