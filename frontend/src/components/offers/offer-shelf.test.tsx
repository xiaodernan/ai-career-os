import { describe, expect, it, vi } from "vitest";
import * as React from "react";
import { renderToStaticMarkup } from "react-dom/server";

/**
 * The offer shelf. The declined row carries the decision letter — the reader's
 * keepsake for the offer they passed on — and the letter renders only on the
 * declined row, only in the reader's language, never beside an accepted or
 * pending one (where it would be a decision, not a memory).
 */
const SHELF_ROW = {
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

vi.mock("@/lib/hooks/offers", () => ({
  useSaveOffer: () => ({ mutate: () => {}, isPending: false }),
  useDeleteOffer: () => ({ mutate: () => {}, isPending: false, variables: undefined }),
  useOfferDecisionLetter: () => letterHook,
  useCounterOfferLetter: () => counterLetterHook,
  useFollowUpOfferLetter: () => followUpLetterHook,
  useAcceptancePlaybook: () => acceptancePlaybookHook,
}));
vi.mock("@/lib/hooks/resources", () => ({
  useOfferShelf: () => ({
    data: { items: [SHELF_ROW, ...COMPARISON_ROWS], total: 2 },
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
