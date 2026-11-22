import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import * as React from "react";
import { renderToStaticMarkup } from "react-dom/server";

import type { OfferShelfItem } from "@/lib/api/types";

/**
 * The offer shelf. The declined row carries the decision letter — the reader's
 * keepsake for the offer they passed on — and the letter renders only on the
 * declined row, only in the reader's language, never beside an accepted or
 * pending one (where it would be a decision, not a memory).
 */
const SHELF_ROW: OfferShelfItem = {
  id: "row-1",
  label: "星海云",
  base: 280000,
  bonus: 40000,
  equity: 60000,
  currency: "CNY",
  remoteType: "hybrid" as const,
  deadline: null,
  notes: "the call felt off",
  totalComp: 380000,
  createdAt: "2026-11-01T00:00:00Z",
  updatedAt: "2026-11-02T00:00:00Z",
  decision: "declined" as const,
};

const COMPARISON_ROWS = [
  { ...SHELF_ROW, id: "row-2", label: "云帆", base: 340000, bonus: 20000, equity: 0, totalComp: 360000, decision: "pending" as const },
];

const letterHook: {
  data: { letter: string | null } | null;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  mutate: any;
  isPending: boolean;
  variables: undefined | { id: string; locale?: string };
} = { data: null, mutate: vi.fn(), isPending: false, variables: undefined };

const counterLetterHook: {
  data: { letter: string | null } | null;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  mutate: any;
  isPending: boolean;
  variables: undefined | { id: string; locale?: string };
} = { data: null, mutate: vi.fn(), isPending: false, variables: undefined };

const followUpLetterHook: {
  data: { letter: string | null } | null;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  mutate: any;
  isPending: boolean;
  variables: undefined | { id: string; locale?: string };
} = { data: null, mutate: vi.fn(), isPending: false, variables: undefined };

const acceptancePlaybookHook: {
  data: { playbook: string | null } | null;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  mutate: any;
  isPending: boolean;
  variables: undefined | { id: string; locale?: string };
} = { data: null, mutate: vi.fn(), isPending: false, variables: undefined };

const negotiationPrepHook: {
  data: { prep: string | null } | null;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  mutate: any;
  isPending: boolean;
  variables: undefined | { id: string; locale?: string };
} = { data: null, mutate: vi.fn(), isPending: false, variables: undefined };

const declineLetterHook: {
  data: { letter: string | null } | null;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  mutate: any;
  isPending: boolean;
  variables: undefined | { id: string; locale?: string };
} = { data: null, mutate: vi.fn(), isPending: false, variables: undefined };

vi.mock("@/lib/hooks/offers", () => ({
  useSaveOffer: () => ({ mutate: () => {}, isPending: false }),
  useDeleteOffer: () => ({ mutate: () => {}, isPending: false, variables: undefined }),
  useOfferDecisionLetter: () => letterHook,
  useCounterOfferLetter: () => counterLetterHook,
  useFollowUpOfferLetter: () => followUpLetterHook,
  useAcceptancePlaybook: () => acceptancePlaybookHook,
  useNegotiationPrep: () => negotiationPrepHook,
  useOfferDeclineLetter: () => declineLetterHook,
}));
let shelfRows = [SHELF_ROW, ...COMPARISON_ROWS];

vi.mock("@/lib/hooks/resources", () => ({
  useOfferShelf: () => ({
    data: { items: shelfRows, total: shelfRows.length },
    isPending: false,
    isError: false,
    refetch: () => {},
  }),
}));
vi.mock("@/components/offers/offer-celebration", () => ({
  OfferCelebration: () => null,
}));

import { OfferShelf } from "./offer-shelf";
import { LocaleProvider } from "@/lib/i18n/locale-context";

function render(locale: "en" | "zh"): string {
  vi.stubGlobal("window", {
    localStorage: { getItem: () => locale, setItem: () => {} },
  });
  try {
    return renderToStaticMarkup(
      <LocaleProvider>
        <OfferShelf />
      </LocaleProvider>,
    );
  } finally {
    vi.unstubAllGlobals();
  }
}

describe("the offer shelf", () => {
  it("renders the decision letter button on the declined row only", () => {
    const zh = render("zh");
    expect(zh).toContain("写这封信");
    expect(zh).toContain("给未来自己的一封信");
    // Two rows on the shelf; the pending one shows no letter entry point.
    const english = render("en");
    expect(english).toContain("Write the letter");
    expect(english).toContain("addressed to the future you");
  });

  it("renders the counter letter button on the pending row only", () => {
    const en = render("en");
    // The pending row offers the sendable email; the hint carries its own promise.
    expect(en).toContain("Write the counter email");
    expect(en).toContain("the ask, sent tonight");
    const zh = render("zh");
    expect(zh).toContain("写这封反要价信");
  });

  it("renders the follow-up email affordance on the pending row too", () => {
    const en = render("en");
    expect(en).toContain("Write the check-in email");
    expect(en).toContain("One polite email");
    const zh = render("zh");
    expect(zh).toContain("写这封跟进邮件");
  });

  it("renders the negotiation prep affordance on the pending row too", () => {
    const en = render("en");
    expect(en).toContain("Write the prep sheet");
    expect(en).toContain("the number you own");
    const zh = render("zh");
    expect(zh).toContain("写这份备忘单");
  });

  it("renders the gracious decline button on the declined row only", () => {
    const en = render("en");
    expect(en).toContain("Write the decline email");
    expect(en).toContain("a clean and final no");
    const zh = render("zh");
    expect(zh).toContain("写这封婉拒信");
    // The pending row carries the sending affordances, never the decline one.
    expect(render("en").split("Write the decline email").length - 1).toBe(1);
  });

  it("renders the letter itself once the writer answers", () => {
    letterHook.data = { letter: "You passed on 380000 because your bar is higher than the number." };
    // A letter stored on the mutation's own result is what the component renders
    letterHook.mutate = vi.fn((_: unknown, opts: { onSuccess?: (out: { letter?: string | null }) => void }) =>
      opts.onSuccess?.({ letter: "You passed on 380000 because your bar is higher than the number." }));
    const html = render("en");
    // The SSR pass happens without the click, so the button path is the checkable one.
    expect(html).toContain("Write the letter");
    letterHook.data = null;
  });
});

/**
 * Epic 406 — the shelf's clock. It used to print a back-running countdown: a
 * deadline that passed became "-1d left", and the final day before a deadline
 * was rounded up instead of named. The badge now has four states, and this is
 * where the boundary between them is pinned.
 */
describe("the shelf's clock", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-11-22T10:00:00Z"));
  });

  afterEach(() => {
    shelfRows = [SHELF_ROW, ...COMPARISON_ROWS];
    vi.useRealTimers();
  });

  it("counts whole days still ahead", () => {
    shelfRows = [{ ...SHELF_ROW, deadline: "2026-11-25T10:00:00Z" }];
    expect(render("en")).toContain("3d left");
    expect(render("zh")).toContain("剩 3 天");
  });

  it("names the last day instead of printing a zero", () => {
    shelfRows = [{ ...SHELF_ROW, deadline: "2026-11-22T22:00:00Z" }];
    expect(render("en")).toContain("Last day");
    expect(render("en")).not.toContain("0d left");
    expect(render("zh")).toContain("今天截止");
  });

  it("says expired instead of counting backwards", () => {
    shelfRows = [{ ...SHELF_ROW, deadline: "2026-11-20T10:00:00Z" }];
    expect(render("en")).toContain("Expired");
    expect(render("en")).not.toContain("-2d left");
    expect(render("zh")).toContain("已过期");
  });

  it("draws no clock for a row without a readable deadline", () => {
    shelfRows = [{ ...SHELF_ROW, deadline: null }];
    const withoutDate = render("en");
    shelfRows = [{ ...SHELF_ROW, deadline: "not a date" }];
    const brokenDate = render("en");
    for (const html of [withoutDate, brokenDate]) {
      expect(html).not.toContain("d left");
      expect(html).not.toContain("Expired");
      expect(html).not.toContain("Last day");
    }
  });
});
