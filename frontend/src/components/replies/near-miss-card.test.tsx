import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

vi.mock("@/lib/i18n/locale-context", () => ({
  useLocale: () => ({
    locale: "en",
    t: (key: string, vars?: Record<string, unknown>) =>
      vars ? `[${key}|${Object.entries(vars).map(([k, v]) => `${k}=${v}`).join(",")}]` : `[${key}]`,
    setLocale: () => undefined,
  }),
}));

vi.mock("sonner", () => ({ toast: { success: vi.fn(), info: vi.fn(), error: vi.fn() } }));

import { NearMissCard } from "./near-miss-card";

describe("NearMissCard", () => {
  const html = renderToStaticMarkup(<NearMissCard />);

  it("renders the shelf, its fields, and its five-slot meter", () => {
    expect(html).toContain('data-testid="near-miss-card"');
    expect(html).toContain("[replies.nearTitle]");
    expect(html).toContain("[replies.nearDescription]");
    expect(html).toContain("[replies.nearRole]");
    expect(html).toContain("[replies.nearCompany]");
    expect(html).toContain("[replies.nearAgain]");
    expect(html).toContain("[replies.nearLearned]");
    expect(html).toContain("[replies.nearChanged]");
    expect(html).toContain("[replies.nearProgress|done=0,total=5]");
    expect(html).toContain('role="progressbar"');
    expect(html).toContain('aria-valuenow="0"');
  });

  it("shows the two-button again toggle, pressed state unknown until chosen", () => {
    expect(html).toContain('aria-pressed="false"');
    expect(html).toContain("[replies.nearAgainYes]");
    expect(html).toContain("[replies.nearAgainNo]");
  });

  it("placeholders quote the reader's page, never invented examples", () => {
    expect(html).not.toContain("Acme was a good fit");
    expect(html).toContain('placeholder="[replies.nearRolePlaceholder]"');
    expect(html).toContain('placeholder="[replies.nearLearnedPlaceholder]"');
    expect(html).toContain('placeholder="[replies.nearChangedPlaceholder]"');
  });
});
