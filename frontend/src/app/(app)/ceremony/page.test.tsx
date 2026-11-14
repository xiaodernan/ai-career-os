import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

vi.mock("@/lib/i18n/locale-context", () => ({
  LocaleProvider: ({ children }: { children: React.ReactNode }) => children,
  useLocale: () => ({
    locale: "en",
    t: (key: string, vars?: Record<string, unknown>) =>
      key.startsWith("ceremony.dateLine")
        ? "Written 2026-11-14, on purpose."
        : vars
          ? `[${key}|${Object.values(vars).join(",")}]`
          : `[${key}]`,
    setLocale: () => undefined,
  }),
}));

const state = vi.hoisted(() => ({
  apps: { data: { items: [] as unknown[], total: 17 }, isPending: false, isError: false } as any,
  interviews: { data: { items: [], total: 9 }, isPending: false, isError: false } as any,
  offers: { data: { items: [] as unknown[], total: 0 }, isPending: false, isError: false } as any,
  letters: { data: { items: [], total: 3 }, total: 3, isPending: false, isError: false, refetch: () => {} } as any,
  notes: { data: { items: [], total: 23 }, isPending: false, isError: false } as any,
  heatmap: {
    data: {
      days: 366,
      grid: [
        { date: "2026-05-01", applications: 1, interviews: 0, replies: 0, aiCalls: 0 },
        { date: "2026-05-05", applications: 0, interviews: 1, replies: 0, aiCalls: 0 },
        { date: "2026-06-02", applications: 0, interviews: 0, replies: 0, aiCalls: 5 },
      ],
      streak: { current: 4, longest: 11 },
      grandTotal: 77,
    },
    isPending: false,
    isError: false,
  } as any,
}));

vi.mock("@/lib/hooks/resources", () => ({
  useApplications: () => state.apps,
  useInterviewSessions: () => state.interviews,
  useOfferShelf: () => state.offers,
  useKnowledgeNotes: () => state.notes,
}));

vi.mock("@/lib/hooks/letters", () => ({
  useLetters: () => state.letters,
}));

vi.mock("@/lib/hooks/monitoring", () => ({
  useActivityHeatmap: () => state.heatmap,
}));

import CeremonyPage from "./page";
import { LocaleProvider } from "@/lib/i18n/locale-context";

beforeEach(() => {
  state.apps = { data: { items: [], total: 17 }, isPending: false, isError: false };
  state.interviews = { data: { items: [], total: 9 }, isPending: false, isError: false };
  state.offers = { data: { items: [], total: 0 }, isPending: false, isError: false };
  state.letters = { data: { items: [], total: 3 }, total: 3, isPending: false, isError: false, refetch: () => {} };
  state.notes = { data: { items: [], total: 23 }, isPending: false, isError: false };
  state.heatmap = {
    data: {
      days: 366,
      grid: [
        { date: "2026-05-01", applications: 1, interviews: 0, replies: 0, aiCalls: 0 },
        { date: "2026-05-05", applications: 0, interviews: 1, replies: 0, aiCalls: 0 },
        { date: "2026-06-02", applications: 0, interviews: 0, replies: 0, aiCalls: 5 },
      ],
      streak: { current: 4, longest: 11 },
      grandTotal: 77,
    },
    isPending: false,
    isError: false,
  };
});

function render() {
  return renderToStaticMarkup(
    <LocaleProvider>
      <CeremonyPage />
    </LocaleProvider>
  );
}

describe("the closing ceremony", () => {
  it("renders every one of the figures, bound to real query answers", () => {
    const html = render();

    expect(html).toContain("17");
    expect(html).toContain("9");
    expect(html).toContain("3");
    expect(html).toContain("23");
    // Days showed up: three grid rows have non-zero actions.
    expect(html).toContain(">3<");
    // And the grand total rides along at the foot of the page.
    expect(html).toContain("77");
  });

  it("names the reader's accepted offer when one exists", () => {
    state.offers = {
      data: {
        items: [
          {
            id: "o1",
            label: "Lunar Works — Staff Engineer",
            base: 200000,
            bonus: 20000,
            equity: 40000,
            currency: "USD",
            remoteType: "hybrid",
            deadline: null,
            notes: null,
            totalComp: 260000,
            decision: "accepted",
          },
        ],
        total: 1,
      },
      isPending: false,
      isError: false,
    };

    const html = render();

    expect(html).toContain("[ceremony.letterPara2Accepted|1]");
  });

  it("reads pending honestly when nothing is accepted yet", () => {
    const html = render();

    expect(html).toContain("[ceremony.letterPara2Pending|0]");
  });

  it("still renders the keepsake when the shelf query is still in flight", () => {
    state.offers = { data: undefined, isPending: true, isError: false };
    const html = render();

    expect(html).toContain("ceremony.statApplications");
    expect(html).not.toContain("[ceremony.letterPara2Accepted");
  });
});
