import { describe, expect, it, vi } from "vitest";
import { readFileSync } from "node:fs";
import { renderToStaticMarkup } from "react-dom/server";

vi.mock("@/lib/hooks/offers", () => {
  const mutation = () => ({ mutate: vi.fn(), isPending: false, variables: undefined });
  return {
    useSaveOffer: mutation,
    useDeleteOffer: mutation,
    useOfferDecisionLetter: mutation,
    useCounterOfferLetter: mutation,
    useFollowUpOfferLetter: mutation,
    useAcceptancePlaybook: mutation,
    useNegotiationPrep: mutation,
    useOfferDeclineLetter: mutation,
  };
});

vi.mock("@/lib/hooks/resources", () => ({
  useOfferShelf: () => ({
    isPending: false,
    data: {
      items: [
        { id: "accepted", label: "Acme — Staff Engineer", base: 100, bonus: 0, equity: 0, currency: "USD", remoteType: "remote", deadline: null, totalComp: 100, decision: "accepted" },
        { id: "pending", label: "Beacon — Staff Engineer", base: 110, bonus: 0, equity: 0, currency: "USD", remoteType: "hybrid", deadline: null, totalComp: 110, decision: "pending" },
        { id: "declined", label: "Cedar — Staff Engineer", base: 90, bonus: 0, equity: 0, currency: "USD", remoteType: "onsite", deadline: null, totalComp: 90, decision: "declined" },
      ],
    },
  }),
}));

vi.mock("@/components/offers/offer-celebration", () => ({ OfferCelebration: () => null }));
vi.mock("sonner", () => ({ toast: { success: vi.fn(), info: vi.fn(), error: vi.fn() } }));

import { LocaleProvider, lookup } from "@/lib/i18n/locale-context";
import { translations } from "@/lib/i18n/translations";
import { OfferShelf } from "./offer-shelf";
import { OfferDayOnePacket } from "./offer-day-one-packet";
import { OfferFirstQuarter } from "./offer-first-quarter";
import { OfferReplies } from "./offer-replies";
import { OfferDecisionLedger } from "./offer-decision-ledger";
import { OfferRehearsalCard } from "./offer-rehearsal-card";
import { OfferCommitmentCard } from "./offer-commitment-card";

const HINT_KEYS = [
  "hintRoleInput", "hintLocationInput", "hintOfferBaseInput", "hintMatchInput", "hintOfferLabelsInput",
  "hintBenchmark", "hintNegotiate", "hintCounter", "hintCompare", "hintPrintPacket",
  "hintShelfDecision_pending", "hintShelfDecision_accepted", "hintShelfDecision_declined",
  "hintShelfLabelInput", "hintShelfBaseInput", "hintShelfBonusInput", "hintShelfEquityInput",
  "hintShelfRemote", "hintShelfSave", "hintShelfEdit", "hintShelfDelete", "hintCounterLetter",
  "hintFollowUpLetter", "hintDeclineLetter", "hintAcceptancePlaybook", "hintShelfLetter", "hintCopyDraft",
  "hintDayOneToggle", "hintDayOneReset", "hintQuarterToggle", "hintQuarterReset",
  "hintReplyRead", "hintReplyCopy", "hintReplyDownload", "hintReplyMailto",
  "hintLedgerWeight", "hintLedgerScore", "hintLedgerNewCriterion", "hintLedgerAdd", "hintLedgerReset", "hintLedgerRemove",
  "hintRehearsalReply", "hintRehearsalNext", "hintRehearsalVerdict", "hintRehearsalKeep", "hintRehearsalReset",
  "hintCommitmentInput", "hintCommitmentSave", "hintCommitmentReset", "hintCelebrationContinue", "hintCelebrationDismiss",
] as const;

function render(locale: "en" | "zh", children: React.ReactNode): string {
  return renderToStaticMarkup(
    <LocaleProvider initialLocale={locale} table={translations[locale]}>
      {children}
    </LocaleProvider>,
  );
}

function source(name: string): string {
  return readFileSync(new URL(`./${name}.tsx`, import.meta.url), "utf8");
}

describe("offers teaching hints", () => {
  it("defines all 51 consequences in both languages", () => {
    expect(HINT_KEYS).toHaveLength(51);
    for (const locale of ["en", "zh"] as const) {
      for (const key of HINT_KEYS) {
        expect(lookup(translations[locale], `offers.${key}`), `${locale}: ${key}`).toBeTruthy();
      }
    }
  });

  it("attaches triggers to every day-one and first-quarter checkbox", () => {
    for (const locale of ["en", "zh"] as const) {
      const dayOne = render(locale, <OfferDayOnePacket />);
      expect(dayOne.match(/aria-pressed="false"/g)).toHaveLength(7);
      expect(dayOne.match(/data-slot="tooltip-trigger"/g)).toHaveLength(7);
      const quarter = render(locale, <OfferFirstQuarter />);
      expect(quarter.match(/aria-pressed="false"/g)).toHaveLength(18);
      expect(quarter.match(/data-slot="tooltip-trigger"/g)).toHaveLength(18);
    }
  });

  it("covers shelf decisions, fields, generators and copy paths without hiding control state", () => {
    for (const locale of ["en", "zh"] as const) {
      const html = render(locale, <OfferShelf />);
      expect(html.match(/data-slot="tooltip-trigger"/g)).toHaveLength(30);
      expect(html.match(/aria-pressed="(?:true|false)"/g)).toHaveLength(9);
      expect(html).toContain('data-slot="select-trigger"');
      expect(html).toContain('id="offer-shelf-remote"');
    }
    const shelf = source("offer-shelf");
    for (const key of ["hintShelfRemote", "hintShelfSave", "hintShelfDelete", "hintCounterLetter", "hintFollowUpLetter", "hintDeclineLetter", "hintAcceptancePlaybook", "hintShelfLetter"]) {
      expect(shelf).toMatch(new RegExp(`<Hint anchor="span"[^>]*label=\\{t\\("offers\\.${key}"\\)\\}>`));
    }
    expect(shelf).not.toContain("chrome.editHint");
    expect(shelf).not.toContain("chrome.deleteHint");
  });

  it("covers replies, ledger inputs, rehearsal replies and the weekly commitment", () => {
    for (const locale of ["en", "zh"] as const) {
      expect(render(locale, <OfferReplies />).match(/data-slot="tooltip-trigger"/g)).toHaveLength(2);
      const ledger = render(locale, <OfferDecisionLedger />);
      expect(ledger.match(/data-slot="tooltip-trigger"/g)).toHaveLength(32);
      expect(ledger.match(/data-slot="select-trigger"/g)).toHaveLength(6);
      expect(render(locale, <OfferRehearsalCard />).match(/role="radio"/g)).toHaveLength(3);
      expect(render(locale, <OfferCommitmentCard />).match(/data-slot="tooltip-trigger"/g)).toHaveLength(2);
    }
    expect(source("offer-decision-ledger")).toContain('<Hint anchor="span" label={t("offers.hintLedgerWeight")}>');
    expect(source("offer-replies")).toContain('label={t("offers.hintReplyMailto")}');
    expect(source("offer-commitment-card")).not.toContain("chrome.resetHint");
  });

  it("opens the rehearsal verdict explicitly after the last saved reply", () => {
    const rehearsal = source("offer-rehearsal-card");
    expect(rehearsal).toContain("const done = verdictOpen && answered(state);");
    expect(rehearsal).toContain("setVerdictOpen(true);");
    expect(rehearsal).toContain("setVerdictOpen(false);");
    expect(rehearsal).toContain('t(isLast ? "offers.hintRehearsalVerdict" : "offers.hintRehearsalNext")');
    expect(rehearsal).not.toContain("chrome.resetHint");
  });
});
