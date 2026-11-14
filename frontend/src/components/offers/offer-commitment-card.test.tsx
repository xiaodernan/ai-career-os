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

import { OfferCommitmentCard } from "./offer-commitment-card";

describe("OfferCommitmentCard", () => {
  it("renders the one-line prompt with the week label and the save path", () => {
    const html = renderToStaticMarkup(<OfferCommitmentCard />);
    expect(html).toContain('data-testid="commitment-card"');
    expect(html).toContain("[offers.commitmentTitle]");
    expect(html).toContain("[offers.commitmentPlaceholder]");
    expect(html).toContain("[offers.commitmentSave]");
    expect(html).toContain("[offers.commitmentLabel|");
  });
});
