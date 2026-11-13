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

const state = vi.hoisted(() => ({
  items: [] as Array<{
    id: string;
    label: string;
    base: number;
    bonus: number;
    equity: number;
    currency: string;
    remoteType: "onsite" | "hybrid" | "remote";
    deadline: string | null;
    notes: string | null;
    totalComp: number;
    createdAt: string;
    updatedAt: string;
  }>,
}));

vi.mock("@/lib/hooks/resources", () => ({
  useOfferShelf: () => ({ data: state.items.length ? { items: state.items, total: state.items.length } : undefined, isPending: false, isError: false }),
}));

const mutations = vi.hoisted(() => ({
  savePending: false,
}));

vi.mock("@/lib/hooks/offers", () => ({
  useSaveOffer: () => ({ mutate: () => undefined, isPending: mutations.savePending, variables: null }),
  useDeleteOffer: () => ({ mutate: () => undefined, isPending: false, variables: null }),
}));

import { OfferShelf } from "./offer-shelf";

function item(over: Partial<(typeof state.items)[number]> & { id: string; label: string }) {
  return {
    base: 180000,
    bonus: 10000,
    equity: 20000,
    currency: "USD",
    remoteType: "hybrid" as const,
    deadline: null,
    notes: null,
    totalComp: 210000,
    createdAt: "2026-11-14T00:00:00Z",
    updatedAt: "2026-11-14T00:00:00Z",
    ...over,
  };
}

describe("OfferShelf", () => {
  it("says the shelf is empty and asks for the first row", () => {
    state.items = [];
    const html = renderToStaticMarkup(<OfferShelf />);
    expect(html).toContain("[offers.shelfEmpty]");
    expect(html).toContain("[offers.shelfAdd]");
  });

  it("ranks the best total and spells each row's parts", () => {
    state.items = [
      item({ id: "a", label: "Acme", totalComp: 210000 }),
      item({ id: "b", label: "Globex", base: 195000, bonus: 0, equity: 0, totalComp: 195000 }),
    ];
    const html = renderToStaticMarkup(<OfferShelf />);

    // The trophy sits on the row the reader is actually deciding between.
    expect(html).toContain("[offers.shelfBest]");
    expect(html).toContain("Acme");
    expect(html).toContain("Globex");
    expect(html).toContain("[offers.shelfCount|2]");
    // The total the compare view ranks by is on every row.
    expect(html).toContain("$210,000");
    expect(html).toContain("$195,000");
  });

  it("warns on the row whose deadline is inside a week", () => {
    const soon = new Date(Date.now() + 3 * 86_400_000).toISOString();
    state.items = [item({ id: "a", label: "Acme", deadline: soon })];
    const html = renderToStaticMarkup(<OfferShelf />);
    expect(html).toContain("text-destructive");
    expect(html).toContain("[offers.shelfDaysLeft|3]");
  });
});
