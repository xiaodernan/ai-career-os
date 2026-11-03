import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import type { InboundMail } from "@/lib/api/types";

const state = vi.hoisted(() => ({
  letters: {
    data: undefined as
      | { items: unknown[]; total: number; page: number; size: number }
      | undefined,
    isPending: false,
    isError: false,
    isFetching: false,
    error: null as unknown,
    refetch: () => {},
  },
  applications: {
    data: undefined as
      | {
          items: { id: string; title: string; companyName: string | null }[];
          total: number;
          page: number;
          size: number;
        }
      | undefined,
    isPending: false,
  },
  url: {
    q: undefined as string | undefined,
    intent: undefined as string | undefined,
    page: 0,
  },
  counts: { data: undefined as Record<string, number> | undefined },
}));

vi.mock("@/lib/hooks/replies", () => ({
  useInboundMails: () => state.letters,
  useInboundIntentCounts: () => state.counts,
  useFileInboundMail: () => ({ mutate: () => {}, isPending: false, variables: undefined }),
}));

// The page's URL state is the one piece SSR cannot hydrate (its effect only runs in a
// browser), so each test hands the page the query it would have adopted. The setter is a
// no-op: these tests read the first paint, they do not press the box.
vi.mock("@/lib/hooks/use-url-state", () => ({
  useUrlState: () => [state.url, () => {}],
}));

vi.mock("@/lib/hooks/resources", () => ({
  useApplications: () => state.applications,
}));

vi.mock("@/lib/hooks/actions", () => ({
  useUpdateApplication: () => ({ mutate: () => {}, isPending: false }),
}));

import RepliesPage from "./page";
import { LocaleProvider } from "@/lib/i18n/locale-context";

/**
 * The replies page is the browser's half of 37.4, and its promise is that every letter
 * says where it belongs: the one the server filed names its card and offers the reading's
 * suggested move behind a confirmation, and the one the server could not narrow waits with
 * a picker instead of landing on the wrong timeline.
 *
 * Rendered through the real locale provider over the real page component: the assertions
 * are the sentences a reader sees, not the keys a mock would hand back.
 */

const ITEMS: InboundMail[] = [
  {
    id: "mail-1",
    fromAddress: "recruiter@acme.test",
    subject: "Re: Backend engineer",
    bodyText: "We would like to schedule a call.",
    intent: "interview",
    company: "Acme",
    role: "Backend engineer",
    suggestedStage: "interview",
    applicationId: "app-1",
    applicationTitle: "Backend engineer",
    receivedAt: "2026-10-27T09:00:00Z",
    filedAt: "2026-10-27T09:05:00Z",
  },
  {
    id: "mail-2",
    fromAddress: "talent@unknown.test",
    subject: "",
    bodyText: "Thanks, but the role is closed.",
    intent: null,
    company: null,
    role: null,
    suggestedStage: null,
    applicationId: null,
    applicationTitle: null,
    receivedAt: "2026-10-26T09:00:00Z",
    filedAt: null,
  },
];

function render(locale: "en" | "zh" = "en"): string {
  vi.stubGlobal("window", {
    localStorage: { getItem: () => locale, setItem: () => {} },
  });
  try {
    return renderToStaticMarkup(
      <LocaleProvider>
        <RepliesPage />
      </LocaleProvider>
    );
  } finally {
    vi.unstubAllGlobals();
  }
}

function withLetters(items: InboundMail[]): void {
  state.letters = {
    data: { items, total: items.length, page: 0, size: 20 },
    isPending: false,
    isError: false,
    isFetching: false,
    error: null,
    refetch: () => {},
  };
}

beforeEach(() => {
  state.url = { q: undefined, intent: undefined, page: 0 };
  state.counts.data = undefined;
  state.letters = {
    data: undefined,
    isPending: false,
    isError: false,
    isFetching: false,
    error: null,
    refetch: () => {},
  };
  state.applications = {
    data: {
      items: [{ id: "app-2", title: "Data engineer", companyName: "Globex" }],
      total: 1,
      page: 0,
      size: 100,
    },
    isPending: false,
  };
});

describe("the replies page", () => {
  it("names the card a filed letter answers and offers its suggested move", () => {
    withLetters(ITEMS);
    const html = render();

    expect(html).toContain("Replies");
    expect(html).toContain("Interview");
    expect(html).toContain("Re: Backend engineer");
    expect(html).toContain("recruiter@acme.test");
    expect(html).toContain("Filed on Backend engineer");
    expect(html).toContain('href="/applications?application=app-1"');
    // The suggestion is advice: it opens the same confirmation every stage move goes through.
    expect(html).toContain("Move to Interview");
    // The letter itself is readable without leaving the page.
    expect(html).toContain("Read the letter");
    expect(html).toContain("We would like to schedule a call.");
  });

  it("asks the reader to pick a card for a letter the server could not file", () => {
    withLetters(ITEMS);
    const html = render();

    // An unread letter says so rather than borrowing one of the classifier's intents.
    expect(html).toContain("Unread");
    expect(html).toContain("A letter with no subject");
    expect(html).toContain("talent@unknown.test");
    // Exactly one picker: the filed letter already has its card.
    expect(html.split('aria-label="Pick the application"').length - 1).toBe(1);
    expect(html).toContain("File");
    expect(html).not.toContain("Filed on talent@unknown.test");
  });

  it("says there is nothing to file on when the board has no applications", () => {
    withLetters([ITEMS[1]]);
    state.applications = { data: { items: [], total: 0, page: 0, size: 100 }, isPending: false };
    const html = render();

    expect(html).toContain("Not filed yet");
    expect(html).not.toContain('aria-label="Pick the application"');
  });

  it("says the same sentences in the reader's language", () => {
    withLetters(ITEMS);
    const html = render("zh");

    expect(html).toContain("回信");
    expect(html).toContain("已归入 Backend engineer");
    expect(html).toContain("移到面试");
    expect(html).toContain("未读");
    expect(html).toContain("一封没有主题的信");
    expect(html).toContain("读这封信");
  });

  it("sends an empty inbox to the settings card that hands out the address", () => {
    withLetters([]);
    const html = render();

    expect(html).toContain("No replies yet");
    expect(html).toContain('href="/settings"');
    expect(html).toContain("Get your address");
  });

  it("puts the typed question in the box and offers to clear it", () => {
    withLetters(ITEMS);
    state.url = { q: "acme", intent: undefined, page: 0 };
    const html = render();

    expect(html).toContain('role="search"');
    expect(html).toContain('value="acme"');
    expect(html).toContain("Search replies");
    expect(html).toContain("Clear search");
  });

  it("says nothing matched instead of sending a searcher to settings", () => {
    // A search that found nothing is not an inbox with nowhere to write: the settings card
    // would hand out an address that solves a problem this reader does not have.
    withLetters([]);
    state.url = { q: "globex", intent: undefined, page: 0 };
    const html = render();

    expect(html).toContain("No replies match “globex”");
    expect(html).toContain("Try a shorter word");
    expect(html).toContain("Clear search");
    expect(html).not.toContain("Get your address");
    expect(html).not.toContain('href="/settings"');
  });

  it("says the search found nothing in the reader's language", () => {
    withLetters([]);
    state.url = { q: "globex", intent: undefined, page: 0 };
    const html = render("zh");

    expect(html).toContain("没有与“globex”匹配的回信");
    expect(html).toContain("清除搜索");
  });

  it("offers every reading as a filter and marks the one in the URL", () => {
    // The chips are the classifier's whole vocabulary, not only the readings present in the
    // page that happens to be loaded: a reading with no letters today must still be askable,
    // and its empty answer says so rather than hiding the question.
    withLetters(ITEMS);
    state.url = { q: "acme", intent: "rejection", page: 0 };

    const html = render();

    expect(html).toContain('role="group"');
    expect(html).toContain("All");
    expect(html).toContain("Unread");
    expect(html).toContain("Rejection");
    expect(html).toContain("Interview");
    expect(html).toContain("Offer");
    expect(html).toContain("Information");
    expect(html).toContain("Other");
    // The picked chip is pressed; "All" is not, even though the words are still on.
    expect(html).toMatch(/aria-pressed="true"[^>]*>Rejection</);
    expect(html).toMatch(/aria-pressed="false"[^>]*>All</);
  });

  it("counts what each chip would show, zeros included", () => {
    // The numbers are answers to the same question as the pages behind them: All sums the
    // readings under the current words, and a zero is printed rather than hidden so a reader
    // knows the chip opens an empty page before they click it.
    withLetters(ITEMS);
    state.counts.data = { unread: 2, rejection: 1, interview: 0, offer: 0, info: 0, other: 0 };

    const html = render();

    expect(html).toMatch(/All<span[^>]*>3</);
    expect(html).toMatch(/Unread<span[^>]*>2</);
    expect(html).toMatch(/Rejection<span[^>]*>1</);
    expect(html).toMatch(/Interview<span[^>]*>0</);
    expect(html).toMatch(/Other<span[^>]*>0</);
  });

  it("says the words and the reading together matched nothing", () => {
    // Under a chip, "clear the search" would leave the reader on the same empty page: the
    // one escape offers to drop both filters, and does not send them to the settings card.
    withLetters([]);
    state.url = { q: "globex", intent: "rejection", page: 0 };

    const html = render();

    expect(html).toContain("No replies match “globex”");
    expect(html).toContain("under this filter");
    expect(html).toContain("Show every letter");
    expect(html).not.toContain("Get your address");
    expect(html).not.toContain('href="/settings"');
  });

  it("names the filter when no letter carries that reading", () => {
    // An empty filter is not an empty inbox: the reader still has an address to hand out.
    withLetters([]);
    state.url = { q: undefined, intent: "unread", page: 0 };

    const html = render("zh");

    expect(html).toContain("这个筛选下没有回信");
    expect(html).toContain("你选的这个读数下没有信");
    expect(html).toContain("看全部回信");
    expect(html).not.toContain('href="/settings"');
  });
});
