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

import { OfferRehearsalCard } from "./offer-rehearsal-card";

describe("OfferRehearsalCard", () => {
  it("renders step one with the band push and its three replies", () => {
    const html = renderToStaticMarkup(<OfferRehearsalCard />);
    expect(html).toContain('data-testid="rehearsal-room"');
    expect(html).toContain("[offers.rehearsalTitle]");
    expect(html).toContain("[offers.rehearsalStep|1]");
    expect(html).toContain("[offers.rehearsalPush_band]");
    expect(html).toContain("[offers.rehearsalReply_band_hold]");
    expect(html).toContain("[offers.rehearsalReply_band_open]");
    expect(html).toContain("[offers.rehearsalReply_band_concede]");
  });
});
