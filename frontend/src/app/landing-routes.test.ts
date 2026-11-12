import { describe, expect, it } from "vitest";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { join, relative, sep } from "node:path";

/**
 * The landing page's click targets, checked against the router (Epic, follow-up
 * to the fix that repointed the header CTAs from the 404 `/auth/login` and
 * `/auth/register` to the real `/login` and `/register` routes).
 *
 * The failure class is quiet: `<Link href="/auth/login">` is a string, so the
 * type system will not look it up; Next builds fine, and the bug only exists at
 * runtime, when the one page every anonymous visitor reaches offers two buttons
 * that lead to a 404. TypeScript and the copy gate (landing-page.test.ts) are
 * both blind to it by construction.
 *
 * So the gate derives the route table the same way Next does — walk the
 * filesystem for `page.tsx` files, strip the `(group)/` route segments, drop the
 * `page.tsx` leaf — and asserts every literal `href="/..."` in the page exists.
 * Dynamic segments (`[id]`) yield no concrete route here, which is honest: a
 * literal link into a dynamic segment would be an authoring error anyway.
 */

const APP_DIR = fileURLToPath(new URL(".", import.meta.url));
const LANDING = fileURLToPath(new URL("./landing-page.tsx", import.meta.url));

/** Every route path Next can serve, derived from the filesystem. */
function routesOf(dir: string): string[] {
  const out: string[] = [];
  const walk = (current: string) => {
    for (const entry of readdirSync(current)) {
      const full = join(current, entry);
      if (statSync(full).isDirectory()) {
        walk(full);
        continue;
      }
      if (entry !== "page.tsx" && entry !== "page.ts") continue;
      const rel = relative(APP_DIR, current)
        .split(sep)
        .filter((part) => part && !/^\(.+\)$/.test(part)) // (auth), (app): route groups are not paths
        .filter((part) => !/^\[.+\]$/.test(part)); // dynamic segments match nothing literally
      out.push("/" + rel.join("/"));
    }
  };
  walk(dir);
  return out;
}

/** Every literal absolute href the landing page names. */
function literalHrefs(source: string): string[] {
  const found = [...source.matchAll(/href="\/([^"]*)"/g)].map((m) => "/" + m[1]);
  return [...new Set(found)].sort();
}

describe("the landing page's click targets", () => {
  const routes = routesOf(APP_DIR);
  const source = readFileSync(LANDING, "utf-8");
  const hrefs = literalHrefs(source);

  it("offers at least one literal in-app target (a page with none would pass vacuously)", () => {
    expect(hrefs.length).toBeGreaterThan(0);
  });

  it("derives a route table that knows the front door", () => {
    // If the walker broke, every assertion below would fail open. Pin the
    // table against two routes the product cannot ship without.
    expect(routes).toContain("/login");
    expect(routes).toContain("/register");
  });

  it("every literal target it names is a route Next can serve", () => {
    const missing = hrefs.filter((href) => !routes.includes(href));
    expect(missing).toEqual([]);
  });
});
