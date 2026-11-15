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

import { PreinterviewKit } from "./preinterview-kit";

describe("PreinterviewKit", () => {
  const html = renderToStaticMarkup(<PreinterviewKit companyId="co-1" />);

  it("renders the five lenses and the meter, never invented content", () => {
    expect(html).toContain('data-testid="preinterview-kit"');
    for (const lens of ["Money", "Role", "Year", "Proof", "Bet"]) {
      expect(html).toContain(`[companies.preread${lens}Label]`);
    }
    for (const lens of ["Money", "Role", "Year", "Proof", "Bet"]) {
      expect(html).toContain(`[companies.preread${lens}Hint]`);
    }
    expect(html).toContain("companies.prereadCount|done=0");
    expect(html).toContain('role="progressbar"');
    expect(html).toContain('aria-valuenow="0"');
  });

  it("quotes the gate sentence when nothing is sealed yet", () => {
    expect(html).toContain("[companies.prereadGate]");
    expect(html).not.toContain("[companies.prereadGather]");
  });

  it("renders placeholders derived from the lens sentences, not from training data", () => {
    for (const lens of ["Money", "Role", "Year", "Proof", "Bet"]) {
      expect(html).toContain(`placeholder="[companies.preread${lens}Hint]"`);
    }
  });
});
