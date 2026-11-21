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

vi.mock("@/lib/onboarding", () => ({
  needsQuickStart: () => false,
  markQuickStartSeen: () => undefined,
}));

import { QUICK_START_EVENT, QuickStart } from "./quick-start";

describe("QuickStart", () => {
  it("exposes the replay event so the topbar can reopen the guide", () => {
    expect(QUICK_START_EVENT).toBe("careeros:open-quick-start");
  });

  it("renders cleanly on the server (closed on first paint, opened by effect in the browser)", () => {
    // The Sheet portals only when open, and `open` is set by a client-only effect,
    // so SSR correctly renders nothing — the important contract is that it does
    // not throw and stays out of the server markup (no hydration tear).
    expect(() => renderToStaticMarkup(<QuickStart />)).not.toThrow();
    const html = renderToStaticMarkup(<QuickStart />);
    expect(html).not.toContain("quick-start-sheet");
  });
});
