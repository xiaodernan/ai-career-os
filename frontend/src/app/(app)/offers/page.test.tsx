import { describe, expect, it, vi } from "vitest";
import * as React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { readFileSync } from "node:fs";

/**
 * The offer-comparison block on the offers page.
 *
 * The engine emits `offers` / `bestByComp` / `narrative` — not `rows` / `best`.
 * The page read `rows` for its whole life and painted the comparison as an
 * empty state every single time. These tests pin the keys the engine writes.
 */
const COMPARISON = {
  currency: "CNY",
  sampleSize: 41,
  bestByComp: "Offer A",
  offers: [
    { label: "Offer A", base: 280000, bonus: 40000, firstYearCash: 320000,
      annualEquity: 60000, totalComp: 380000, assessment: { verdict: "above_market" } },
    { label: "Offer B", base: 340000, bonus: 20000, firstYearCash: 360000,
      annualEquity: 0, totalComp: 360000, assessment: { verdict: "within_market" } },
  ],
  notes: ["Above the market band: Offer A"],
  narrative: "Offer A totals 380000 against B's 360000 — the 60000 of equity is the whole gap.",
};

const hookState: { data: unknown } = { data: COMPARISON };
vi.mock("@/lib/hooks/offers", () => ({
  useSalaryBenchmark: () => ({ mutate: () => {}, isPending: false, data: undefined }),
  useNegotiate: () => ({ mutate: () => {}, isPending: false, data: undefined }),
  useCounterOffer: () => ({ mutate: () => {}, isPending: false, data: undefined }),
  useCompareOffers: () => ({
    mutate: () => {},
    isPending: false,
    data: hookState.data,
  }),
}));
vi.mock("@/components/offers/offer-shelf", () => ({ OfferShelf: () => null }));
vi.mock("@/components/offers/offer-day-one-packet", () => ({ OfferDayOnePacket: () => null }));
vi.mock("@/components/offers/offer-first-quarter", () => ({ OfferFirstQuarter: () => null }));
vi.mock("@/components/offers/offer-replies", () => ({ OfferReplies: () => null }));
vi.mock("@/components/offers/offer-decision-ledger", () => ({ OfferDecisionLedger: () => null }));
vi.mock("@/components/offers/offer-rehearsal-card", () => ({ OfferRehearsalCard: () => null }));
vi.mock("@/components/offers/offer-commitment-card", () => ({ OfferCommitmentCard: () => null }));

import OffersPage from "./page";
import { LocaleProvider } from "@/lib/i18n/locale-context";

function render(locale: "en" | "zh"): string {
  vi.stubGlobal("window", {
    localStorage: { getItem: () => locale, setItem: () => {} },
  });
  try {
    return renderToStaticMarkup(
      <LocaleProvider>
        <OffersPage />
      </LocaleProvider>
    );
  } finally {
    vi.unstubAllGlobals();
  }
}

describe("the offer comparison block", () => {
  it("draws the comparison as the engine answered it, en and zh", () => {
    hookState.data = COMPARISON;
    const en = render("en");
    expect(en).toContain("Offer A leads on total compensation.");
    expect(en).not.toContain("No offers to compare");
    expect(en).toContain("The editor says");
    expect(en).toContain("the 60000 of equity is the whole gap");

    const zh = render("zh");
    expect(zh).toContain("编辑说");
    expect(zh).toContain("the 60000 of equity is the whole gap");
  });

  it("silence from the editor costs the paragraph, never the ranking", () => {
    hookState.data = { ...COMPARISON, narrative: null };
    const en = render("en");
    expect(en).toContain("Offer A leads on total compensation.");
    expect(en).not.toContain("The editor says");
    hookState.data = COMPARISON;
  });

  it("keeps the honest empty state when the comparison has no offers", () => {
    hookState.data = { ...COMPARISON, offers: [] };
    expect(render("en")).toContain("No offers to compare");
    hookState.data = COMPARISON;
  });

  it("attaches bilingual consequence hints without replacing input or loading state", () => {
    for (const locale of ["en", "zh"] as const) {
      const html = render(locale);
      expect(html.match(/data-slot="tooltip-trigger"/g)).toHaveLength(10);
      expect(html.match(/data-slot="input"/g)).toHaveLength(4);
      expect(html).toContain('id="offer-role"');
      expect(html).toContain('id="offer-labels"');
    }
    const source = readFileSync(new URL("./page.tsx", import.meta.url), "utf8");
    for (const key of ["hintRoleInput", "hintLocationInput", "hintOfferBaseInput", "hintMatchInput", "hintOfferLabelsInput", "hintBenchmark", "hintNegotiate", "hintCounter", "hintCompare"]) {
      expect(source).toContain(`<Hint anchor="span" label={t("offers.${key}")}>`);
    }
    expect(source).toContain('<Hint label={t("offers.hintPrintPacket")}>');
  });
});
