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

/**
 * Epic 401 — the walk grew a fifth beat. The quick start is a server-safe sheet,
 * so the contract this test can honestly grade is the step list itself: five
 * beats, each with a real route, and the calendar among them.
 */
import { QUICK_START_EVENT, QUICK_START_STEPS, QuickStart } from "./quick-start";

describe("QuickStart", () => {
  it("exposes the replay event so the topbar can reopen the guide", () => {
    expect(QUICK_START_EVENT).toBe("careeros:open-quick-start");
  });

  it("walks five beats and points the fifth at the calendar", () => {
    expect(QUICK_START_STEPS).toHaveLength(5);
    expect(QUICK_START_STEPS[4].titleKey).toBe("quickstart.step5Title");
    expect(QUICK_START_STEPS[4].hrefKey).toBe("quickstart.step5Href");
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
