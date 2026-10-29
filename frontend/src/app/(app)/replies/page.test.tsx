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
}));

vi.mock("@/lib/hooks/replies", () => ({
  useInboundMails: () => state.letters,
  useFileInboundMail: () => ({ mutate: () => {}, isPending: false, variables: undefined }),
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
});
