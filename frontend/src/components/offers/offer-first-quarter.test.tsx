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

const state = vi.hoisted(() => ({
  items: [] as Array<Record<string, unknown>>,
}));

vi.mock("@/lib/hooks/resources", () => ({
  useOfferShelf: () => ({
    data: state.items.length ? { items: state.items, total: state.items.length } : undefined,
    isPending: false,
    isError: false,
  }),
}));

import { OfferFirstQuarter } from "./offer-first-quarter";

function acceptedRow() {
  return {
    id: "offer-1",
    label: "Acme — Senior Backend",
    base: 220000,
    bonus: 18000,
    equity: 40000,
    currency: "USD",
    remoteType: "hybrid",
    deadline: null,
    notes: null,
    totalComp: 278000,
    createdAt: "2026-11-14T00:00:00Z",
    updatedAt: "2026-11-14T00:00:00Z",
    decision: "accepted",
  };
}

beforeEach(() => {
  state.items = [];
});

describe("OfferFirstQuarter", () => {
  it("renders nothing before any offer is accepted", () => {
    state.items = [{ ...acceptedRow(), decision: "pending" }];
    expect(renderToStaticMarkup(<OfferFirstQuarter />)).toBe("");
  });

  it("renders nothing when the shelf has no data at all", () => {
    state.items = [];
    expect(renderToStaticMarkup(<OfferFirstQuarter />)).toBe("");
  });

  it("renders the three acts, every tick and an honest zero meter once accepted", () => {
    state.items = [acceptedRow()];
    const html = renderToStaticMarkup(<OfferFirstQuarter />);

    expect(html).toContain('data-testid="first-quarter"');
    expect(html).toContain("[offers.quarterActLand]");
    expect(html).toContain("[offers.quarterActOwn]");
    expect(html).toContain("[offers.quarterActLift]");
    expect(html).toContain("[offers.quarterLand1]");
    expect(html).toContain("[offers.quarterLand6]");
    expect(html).toContain("[offers.quarterOwn1]");
    expect(html).toContain("[offers.quarterLift6]");
    expect(html).toContain('role="progressbar"');
    expect(html).toContain('aria-valuenow="0"');
  });
});
