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

import { OfferReplies, splitLabelForTest } from "./offer-replies";

function rows(decision: "accepted" | "declined" | "pending") {
  return [
    {
      id: "o-1",
      label: "Lunar Works — Staff Engineer",
      base: 230000,
      bonus: 30000,
      equity: 50000,
      currency: "USD",
      remoteType: "hybrid" as const,
      deadline: null,
      notes: null,
      totalComp: 310000,
      createdAt: "2026-11-14T00:00:00Z",
      updatedAt: "2026-11-14T00:00:00Z",
      decision,
    },
  ];
}

beforeEach(() => {
  state.items = [];
});

describe("OfferReplies — the bookend", () => {
  it("renders nothing when every row is still pending", () => {
    state.items = rows("pending");
    expect(renderToStaticMarkup(<OfferReplies />)).toBe("");
  });

  it("renders nothing when the shelf is empty", () => {
    state.items = [];
    expect(renderToStaticMarkup(<OfferReplies />)).toBe("");
  });

  it("splits hyphenated labels ('Acme - Senior Backend') into company and role", () => {
    state.items = [
      {
        ...rows("accepted")[0],
        id: "o-hyphen",
        label: "Lunar Works - Staff Engineer",
      },
    ];
    const html = renderToStaticMarkup(<OfferReplies />);

    expect(html).toContain("reply-yes");
    // The company travels whole; the role travels as the interpolated value.
    expect(html).toContain("Lunar Works");
    expect(html).toContain("Staff Engineer");
  });

  it("falls back to the generic role fallback when the label is bare", () => {
    expect(splitLabelForTest("Lunar Works").role).toBe("");
    expect(splitLabelForTest("Lunar Works").company).toBe("Lunar Works");
  });

  it("writes the yes when a row is accepted, named from the reader's own label", () => {
    state.items = rows("accepted");
    const html = renderToStaticMarkup(<OfferReplies />);

    expect(html).toContain('data-testid="offer-replies"');
    expect(html).toContain("reply-yes");
    expect(html).toContain("Lunar Works");
  });

  it("writes the no for each declined row, one card per declined company", () => {
    state.items = [
      { ...rows("declined")[0], id: "o-1", label: "Lunar Works — Staff Engineer" },
      { ...rows("declined")[0], id: "o-2", label: "Globex — Principal SRE" },
    ];
    const html = renderToStaticMarkup(<OfferReplies />);

    expect(html).toContain("Lunar Works");
    expect(html).toContain("Globex");
    expect((html.match(/data-testid="reply-no"/g) ?? []).length).toBe(2);
  });
});
