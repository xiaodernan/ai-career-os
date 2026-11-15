import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

vi.mock("next/navigation", () => ({
  usePathname: () => "/dashboard",
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn(), forward: vi.fn(), refresh: vi.fn(), prefetch: vi.fn() }),
}));

vi.mock("@/lib/i18n/locale-context", () => ({
  useLocale: () => ({
    locale: "en",
    t: (key: string, vars?: Record<string, unknown>) =>
      vars ? `[${key}|${Object.values(vars).join(",")}]` : `[${key}]`,
    setLocale: () => undefined,
  }),
}));

import { ManualSheet } from "./open-manual";

describe("ManualSheet", () => {
  it("renders the topbar manual button with its accessible name", () => {
    const html = renderToStaticMarkup(<ManualSheet />);
    expect(html).toContain('data-testid="manual-open-button"');
    expect(html).toContain("[chrome.manualOpen]");
  });
});
