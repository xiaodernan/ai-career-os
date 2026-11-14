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

vi.mock("sonner", () => ({ toast: { success: vi.fn(), info: vi.fn(), error: vi.fn() } }));

import { PocketCard } from "./pocket-card";

describe("PocketCard", () => {
  it("renders the pocket with its four families, restore path and download path", () => {
    const html = renderToStaticMarkup(<PocketCard />);
    expect(html).toContain('data-testid="pocket-card"');
    expect(html).toContain("[data.pocketTitle]");
    expect(html).toContain("[data.pocketFamilyLedger]");
    expect(html).toContain("[data.pocketFamilyQuarter]");
    expect(html).toContain("[data.pocketFamilyDayOne]");
    expect(html).toContain("[data.pocketFamilyDebrief]");
    expect(html).toContain("[data.pocketDownload]");
    expect(html).toContain("[data.pocketRestore]");
    expect(html).toContain('accept=".json,application/json"');
  });

  it("offers the empty hint when no browser-local artifact exists yet", () => {
    const html = renderToStaticMarkup(<PocketCard />);
    expect(html).toContain("[data.pocketEmpty]");
  });
});
