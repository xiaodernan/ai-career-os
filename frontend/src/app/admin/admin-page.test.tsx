import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

vi.mock("@/lib/i18n/locale-context", () => ({
  useLocale: () => ({
    locale: "en",
    t: (key: string, vars?: Record<string, unknown>) =>
      vars ? `[${key}|${Object.values(vars).join(",")}]` : `[${key}]`,
    setLocale: () => undefined,
  }),
}));

import AdminPage from "./admin-page";

/**
 * The admin ledger used to carry a "golden journey" latency table whose nine rows
 * all had p50 === p95 — impossible for measured data — while its lede claimed
 * "Measured live on this install". That is fabricated data presented as measurement,
 * exactly the "演示数据堆砌" the owner rejects. It has no backing source: journey_api.py
 * prints to stdout and persists nothing. This guard keeps the numbers from creeping back.
 */
describe("AdminPage", () => {
  it("renders the locked gate before the passphrase; the SSR surface never shows the ledger", () => {
    const html = renderToStaticMarkup(<AdminPage />);
    expect(html).toContain("[admin.passphraseLabel]");
    expect(html).toContain("[admin.unlock]");
    expect(html).toContain("[admin.adminTitle]");
    expect(html).not.toContain("[admin.optimizationsTitle]");
    expect(html).not.toContain("[admin.attentionTitle]");
  });

  it("does not present fabricated per-step latencies as measured", () => {
    const source = readFileSync(resolve(__dirname, "./admin-page.tsx"), "utf8");
    for (const fabricated of ["39604", "15226", "STATIONS", "Measured live on this install"]) {
      expect(source, fabricated).not.toContain(fabricated);
    }
  });
});
