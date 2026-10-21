import { existsSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

import { NAV_ITEMS, routeTitle, titleForPath } from "./nav";

const appDir = fileURLToPath(new URL("../../app/(app)/", import.meta.url));

describe("NAV_ITEMS", () => {
  it("has unique hrefs", () => {
    const hrefs = NAV_ITEMS.map((i) => i.href);
    expect(new Set(hrefs).size).toBe(hrefs.length);
  });

  it("every nav link resolves to a real page (no dead links)", () => {
    const missing = NAV_ITEMS.filter(
      ({ href }) => !existsSync(join(appDir, href.replace(/^\//, ""), "page.tsx"))
    ).map((i) => i.href);
    expect(missing).toEqual([]);
  });

  it("every item has a label and description", () => {
    for (const item of NAV_ITEMS) {
      expect(item.label).toBeTruthy();
      expect(item.description).toBeTruthy();
    }
  });
});

describe("titleForPath", () => {
  it("matches exact routes", () => {
    expect(titleForPath("/dashboard")).toBe("Dashboard");
    expect(titleForPath("/copilot")).toBe("Copilot");
  });
  it("matches nested routes by prefix", () => {
    expect(titleForPath("/jobs/123")).toBe("Jobs");
    expect(titleForPath("/resumes/abc/edit")).toBe("Resumes");
  });
  it("does not match a sibling that merely shares a prefix", () => {
    // "/copilotx" must NOT be treated as "/copilot"
    expect(titleForPath("/copilotxyz")).toBe("AI Career OS");
  });
  it("falls back to the product name for unknown paths", () => {
    expect(titleForPath("/nowhere")).toBe("AI Career OS");
  });
});

describe("routeTitle", () => {
  // The browser tab's title. The server cannot read the locale -- it lives
  // in the browser's own storage -- so the route's `metadata` export could
  // only ever name the page in English. The client sets it instead, from
  // this table, in the reader's language.

  const zh = (key: string) =>
    ({
      "nav.dashboard": "仪表盘",
      "nav.jobs": "职位",
      "nav.resumes": "简历",
      "landing.pageTitle": "AI Career OS — 你的个人求职操作系统",
      "auth.pageTitles.signIn": "登录",
      "auth.pageTitles.signUp": "注册账号",
    })[key] ?? key;

  it("names a route in the reader's language", () => {
    expect(routeTitle("/dashboard", zh)).toBe("仪表盘");
    expect(routeTitle("/jobs/123", zh)).toBe("职位");
  });

  it("names the public routes, which are not in the navigation", () => {
    expect(routeTitle("/", zh)).toBe("AI Career OS — 你的个人求职操作系统");
    expect(routeTitle("/login", zh)).toBe("登录");
    expect(routeTitle("/register", zh)).toBe("注册账号");
  });

  it("answers null for a path the product does not name", () => {
    // The null matters: the tab's title belongs to the server's `metadata`
    // for a path the product does not name, and the client must not
    // overwrite the server's answer with a guess.
    expect(routeTitle("/nowhere", zh)).toBeNull();
    expect(routeTitle("/copilotxyz", zh)).toBeNull();
  });

  it("falls back to the English name when the locale does not name the route", () => {
    // A key the table has no name for must not become the title: the raw
    // key in a browser tab is worse than the product's own wording.
    const bare = (key: string) => key;
    expect(routeTitle("/dashboard", bare)).toBe("Dashboard");
    expect(routeTitle("/login", bare)).toBe("Sign in");
  });
});
