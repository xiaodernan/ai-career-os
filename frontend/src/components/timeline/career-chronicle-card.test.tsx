import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

vi.mock("@/lib/i18n/locale-context", () => ({
  useLocale: () => ({ locale: "en", t: (key: string) => `[${key}]`, setLocale: () => undefined }),
}));
const chronicle = vi.hoisted(() => ({
  data: undefined as
    | { chapters: Array<{ key: string; title: string; prose: string; anchor?: string }> }
    | undefined,
}));
vi.mock("@/lib/hooks/timeline", () => ({
  useCareerChronicle: () => ({
    mutate: () => undefined,
    isPending: false,
    isSuccess: chronicle.data !== undefined,
    isError: false,
    data: chronicle.data,
  }),
}));

import { CareerChronicleCard } from "./career-chronicle-card";

const EVENTS = [
  { at: "2026-09-01T09:00:00Z", kind: "application", title: "Backend · Acme", refId: "app-1", summary: "" },
  { at: "2026-09-02T09:00:00Z", kind: "interview", title: "Rehearsal 1", refId: "iv-1", summary: "" },
];

describe("CareerChronicleCard", () => {
  it("renders the locked chronicle with locale-keyed copy", () => {
    chronicle.data = undefined;
    const html = renderToStaticMarkup(
      <CareerChronicleCard
        events={EVENTS}
        milestones={{ milestones: [], counters: { applications: 1, interviewsCompleted: 0, offers: 0, letters: 0, matches: 0, currentStreak: 0, offersOnShelf: 0 } }}
      />
    );
    expect(html).toContain("[timeline.chronicleTitle]");
    expect(html).toContain("[timeline.chronicleLocked]");
    expect(html).toContain("[timeline.chronicleAction]");
  });

  it("370: a chapter's anchor opens onto the region it names", () => {
    // The story and the world are two readings of one ledger. A chapter named what
    // happened and never said where; its own anchor is the join, and the region it
    // places the chapter in is a door onto the map narrowed there.
    chronicle.data = {
      chapters: [{ key: "c1", title: "The first knock", prose: "One application went out.", anchor: "iv-1" }],
    };
    const html = renderToStaticMarkup(
      <CareerChronicleCard events={EVENTS} milestones={null} />
    );
    expect(html).toContain("[timeline.kinds.interview]");
    expect(html).toContain('href="/timeline?kind=interview"');
    expect(html).toContain("[timeline.chronicleRegionDoor]");
  });

  it("370: an anchor the ledger cannot place stays a quiet number", () => {
    // An honest gap, never a guessed region.
    chronicle.data = {
      chapters: [{ key: "c1", title: "A chapter from nowhere", prose: "…", anchor: "no-such-row" }],
    };
    const html = renderToStaticMarkup(
      <CareerChronicleCard events={EVENTS} milestones={null} />
    );
    expect(html).toContain("no-such-row");
    expect(html).not.toContain('href="/timeline?kind=');
  });
});
