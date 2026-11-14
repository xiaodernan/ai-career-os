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

const state = vi.hoisted(() => ({
  items: [] as Array<Record<string, unknown>>,
  pending: false,
}));

vi.mock("@/lib/hooks/resources", () => ({
  useOfferShelf: () => ({
    data: state.items.length ? { items: state.items, total: state.items.length } : undefined,
    isPending: state.pending,
    isError: false,
  }),
}));

import { OfferDecisionLedger } from "./offer-decision-ledger";

function offerRow(id: string, label: string, totalComp: number) {
  return {
    id,
    label,
    base: totalComp - 20000,
    bonus: 12000,
    equity: 8000,
    currency: "USD",
    remoteType: "hybrid",
    deadline: null,
    notes: null,
    totalComp,
    createdAt: "2026-11-15T00:00:00Z",
    updatedAt: "2026-11-15T00:00:00Z",
    decision: "pending",
  };
}

beforeEach(() => {
  state.items = [offerRow("offer-a", "Acme — Staff Engineer", 320000), offerRow("offer-b", "Northwind — Principal", 290000)];
  state.pending = false;
  if (typeof window !== "undefined") window.localStorage.clear();
});

describe("OfferDecisionLedger", () => {
  it("renders the empty shelf line instead of the table when there is no offer to weigh", () => {
    state.items = [];
    const html = renderToStaticMarkup(<OfferDecisionLedger />);
    expect(html).toContain("[offers.ledgerEmptyShelf]");
    expect(html).not.toContain("<table");
    expect(html).toContain('data-testid="decision-ledger"');
  });

  it("renders the starter criteria, both offers and an honest empty meter", () => {
    const html = renderToStaticMarkup(<OfferDecisionLedger />);
    expect(html).toContain('data-testid="decision-ledger"');
    expect(html).toContain("[offers.ledgerCriterion_comp]");
    expect(html).toContain("[offers.ledgerCriterion_growth]");
    expect(html).toContain("[offers.ledgerCriterion_team]");
    expect(html).toContain("[offers.ledgerCriterion_mission]");
    expect(html).toContain("[offers.ledgerCriterion_location]");
    expect(html).toContain("[offers.ledgerCriterion_stability]");
    expect(html).toContain("Acme — Staff Engineer");
    expect(html).toContain("Northwind — Principal");
    expect(html).toContain('role="status"');
    expect(html).toContain("[offers.ledgerNeedScores]");
  });

  it("labels the score inputs with the criterion and the offer", () => {
    const html = renderToStaticMarkup(<OfferDecisionLedger />);
    expect(html).toContain("[offers.ledgerOfferScore|[offers.ledgerCriterion_comp],Acme — Staff Engineer]");
    expect(html).toContain("[offers.ledgerOfferScore|[offers.ledgerCriterion_stability],Northwind — Principal]");
  });

  it("shows the total grid without crowning anyone before a score is typed", () => {
    const html = renderToStaticMarkup(<OfferDecisionLedger />);
    expect(html).not.toContain("[offers.ledgerLeader|");
    expect(html).toContain("[offers.ledgerTotal]");
  });
});
