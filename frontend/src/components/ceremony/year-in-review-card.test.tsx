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

import { YearInReviewCard } from "./year-in-review-card";

const NUMBERS = {
  applications: 37,
  interviews: 9,
  offers: 2,
  letters: 5,
  notes: 11,
  daysShowed: 14,
  grandTotal: 88,
  year: "2026",
};

describe("YearInReviewCard", () => {
  it("renders the four tiles, the grand total and the download path", () => {
    const html = renderToStaticMarkup(<YearInReviewCard numbers={NUMBERS} />);
    expect(html).toContain('data-testid="year-in-review"');
    expect(html).toContain("37");
    expect(html).toContain("9");
    expect(html).toContain("2");
    expect(html).toContain("88");
    expect(html).toContain("[ceremony.reviewDownload]");
    expect(html).toContain("[ceremony.reviewTitle]");
    expect(html).toContain("[ceremony.statApplications]");
    expect(html).toContain("[ceremony.statInterviews]");
    expect(html).toContain("[ceremony.statOffers]");
  });
});
