import { existsSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

import { NAV_ITEMS, PUBLIC_PAGE_TITLES, titleForPath } from "./nav";

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

describe("the public pages' titles", () => {
  // The pages a visitor can reach without signing in. They are not in the
  // navigation -- there is no sidebar for a visitor -- but they are pages
  // the reader can be on, and their title is the same word in the same
  // place as every other page's.
  it("names every public route", () => {
    expect(Object.keys(PUBLIC_PAGE_TITLES).sort()).toEqual([
      "/",
      "/confirm-email",
      "/forgot-password",
      "/login",
      "/register",
      "/reset-password",
    ]);
  });

  it("carries a key and an English fallback for each", () => {
    for (const [path, { key, label }] of Object.entries(PUBLIC_PAGE_TITLES)) {
      expect(key, `${path} has no key`).toBeTruthy();
      expect(label, `${path} has no English name`).toBeTruthy();
    }
  });

  it("names no page that is not public", () => {
    // A signed-in route's title comes from the navigation, not from here.
    for (const path of Object.keys(PUBLIC_PAGE_TITLES)) {
      expect(NAV_ITEMS.some((item) => item.href === path)).toBe(false);
    }
  });
});
