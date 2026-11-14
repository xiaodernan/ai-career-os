import { beforeEach, describe, expect, it, vi } from "vitest";
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

import { DebriefCard } from "./debrief-card";

beforeEach(() => {
  if (typeof window !== "undefined") window.localStorage.clear();
});

describe("DebriefCard", () => {
  it("renders the two fields with their labels, bound to the session's own storage key", () => {
    const html = renderToStaticMarkup(<DebriefCard sessionId="session-1" />);
    expect(html).toContain('data-testid="debrief-card"');
    expect(html).toContain('id="debrief-what-session-1"');
    expect(html).toContain('id="debrief-different-session-1"');
    expect(html).toContain("[interviews.debrief.whatHappened]");
    expect(html).toContain("[interviews.debrief.differently]");
    expect(html).toContain("[interviews.debrief.eyebrow]");
  });

  it("shows the reset path only once a field has words", () => {
    const html = renderToStaticMarkup(<DebriefCard sessionId="session-2" />);
    expect(html).not.toContain("[interviews.debrief.reset]");
    expect(html).not.toContain("[interviews.debrief.savedLocal]");
  });
});
