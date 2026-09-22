import { existsSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

import { NAV_ITEMS, titleForPath } from "./nav";

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
