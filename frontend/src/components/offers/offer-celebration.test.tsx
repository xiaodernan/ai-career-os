"use client";

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

import { OfferCelebration } from "./offer-celebration";

describe("OfferCelebration", () => {
  it("renders nothing when closed", () => {
    expect(renderToStaticMarkup(
      <OfferCelebration open={false} role="Backend Engineer" company="Acme" onContinue={() => {}} />,
    )).toBe("");
  });

  it("names the role and company, points at the offers shelf", () => {
    const html = renderToStaticMarkup(
      <OfferCelebration open role="Backend Engineer" company="Acme" onContinue={() => {}} />,
    );
    expect(html).toContain("[offers.celebrationTitle]");
    expect(html).toContain("[offers.celebrationSubtitle|Backend Engineer,Acme]");
    expect(html).toContain("/offers");
    expect(html).toContain("role=\"dialog\"");
  });

  it("renders all confetti pieces in the markup — never hidden behind JS", () => {
    const html = renderToStaticMarkup(
      <OfferCelebration open role={null} company={null} onContinue={() => {}} />,
    );
    expect((html.match(/confetti-piece/g) ?? []).length).toBeGreaterThanOrEqual(20);
  });

  it("the accepted variant names the answer, links to the packet, keeps the rain", () => {
    const html = renderToStaticMarkup(
      <OfferCelebration open role="Acme — Senior Backend" company={null} variant="accepted" onContinue={() => {}} />,
    );
    expect(html).toContain("[offers.committedTitle]");
    expect(html).toContain("[offers.committedBody]");
    // Role-only subtitle reuses the shared role-line key by design.
    expect(html).toContain("[offers.celebrationSubtitleRole|Acme — Senior Backend]");
    // The one ask points at the first-week packet, not at the shelf the reader is already on.
    expect(html).toContain("#day-one-packet");
    expect(html).not.toContain("[offers.celebrationBody]");
    expect((html.match(/confetti-piece/g) ?? []).length).toBeGreaterThanOrEqual(20);
  });

  it("the accepted variant's aria-label is its own title, not the offer's", () => {
    const html = renderToStaticMarkup(
      <OfferCelebration open role={null} company={null} variant="accepted" onContinue={() => {}} />,
    );
    expect(html).toContain('aria-label="[offers.committedTitle]"');
    expect(html).toContain("[offers.committedSubtitleBare]");
  });
});
