import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import type { InterviewSession } from "@/lib/api/types";

/**
 * The rehearsals board is the browser's half of 70.4, and since 70.5 it asks the question that
 * half was waiting for: the words in the box are the question the server answered, not a filter
 * over the rows already on screen, and the rows are one window of that answer. A client-side
 * filter would silently hide every rehearsal the server found on another page.
 *
 * Rendered through the real locale provider, because the copy is the contract here: the board has
 * three different empties now, and only one of them is allowed to blame the reader's keyboard.
 */

const state = vi.hoisted(() => ({
  sessions: {
    data: undefined as
      | { items: unknown[]; total: number; page: number; size: number }
      | undefined,
    isPending: false,
    isError: false,
    isFetching: false,
    error: null as unknown,
    refetch: () => {},
  },
  // The page reads a partial URL state: a word nobody typed is absent rather than `undefined`, and
  // `useUrlState` is the piece SSR cannot hydrate (its adopt-the-query effect runs only in a
  // browser), so each test hands the page the query string it would have adopted.
  url: {} as { page: number; application?: string; q?: string },
  params: undefined as Record<string, unknown> | undefined,
}));

vi.mock("@/lib/hooks/resources", () => ({
  useInterviewSessions: (params?: Record<string, unknown>) => {
    state.params = params;
    return state.sessions;
  },
}));

vi.mock("@/lib/hooks/actions", () => ({
  useCreateInterviewSession: () => ({ mutate: () => {}, isPending: false }),
  // 66.1: the row's delete verb mounts on every row, so the page needs it too.
  useDeleteInterviewSession: () => ({ mutate: () => {}, isPending: false }),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: () => undefined }),
}));

vi.mock("@/lib/hooks/use-url-state", () => ({
  useUrlState: () => [state.url, () => {}],
}));

import InterviewsPage from "./page";
import { LocaleProvider } from "@/lib/i18n/locale-context";

const ITEMS: InterviewSession[] = [
  {
    id: "s1",
    status: "completed",
    mode: "technical",
    applicationId: "app-9",
    applicationStatus: "interview",
    jobTitle: "Staff Backend Engineer",
    companyName: "Acme Robotics",
    questionCount: 3,
    startedAt: "2026-11-02T09:00:00Z",
    finishedAt: "2026-11-02T10:00:00Z",
    overall: 72,
  },
  {
    id: "s2",
    status: "active",
    mode: "behavioral",
    companyName: "Under_Score Labs",
    questionCount: 1,
    startedAt: "2026-11-03T09:00:00Z",
  },
];

function withSessions(items: InterviewSession[], total: number): void {
  state.sessions = {
    // The window is the server's, not a page the client invented over a bare list (72.1).
    data: { items, total, page: 0, size: 20 },
    isPending: false,
    isError: false,
    isFetching: false,
    error: null,
    refetch: () => {},
  };
}

function render(locale: "en" | "zh" = "en"): string {
  vi.stubGlobal("window", {
    localStorage: { getItem: () => locale, setItem: () => {} },
  });
  try {
    return renderToStaticMarkup(
      <LocaleProvider>
        <InterviewsPage />
      </LocaleProvider>
    );
  } finally {
    vi.unstubAllGlobals();
  }
}

beforeEach(() => {
  state.url = { page: 0 };
  state.params = undefined;
  state.sessions = {
    data: undefined,
    isPending: false,
    isError: false,
    isFetching: false,
    error: null,
    refetch: () => {},
  };
});

describe("the rehearsals board", () => {
  it("asks the route for the word in the box, and shows it back", () => {
    state.url = { page: 0, q: "acme" };
    withSessions([ITEMS[0]], 1);
    const html = render();

    // The word travels beside the window the board asks with -- and it is carried even when nobody
    // has typed one, which is the difference between asking `?q=` and a different route.
    expect(state.params).toEqual({ page: 0, size: 20, applicationId: undefined, q: "acme" });
    expect(html).toContain('role="search"');
    expect(html).toContain('placeholder="Search interviews"');
    expect(html).toContain('aria-label="Search interviews by company, role or mode"');
    expect(html).toContain('value="acme"');
    expect(html).toContain("Clear search");
    expect(html).toContain("Staff Backend Engineer");
    // The box does not displace the row's own actions: a reader mid-search still gets back to the
    // card the rehearsal was started from, which is the point of the board.
    expect(html).toContain('href="/applications?application=app-9"');
    expect(html).toContain("Open application");
    // 57.4: the row names the stage the card is in.
    expect(html).toContain(">Interview<");
  });

  it("renders no clear button and no question when the reader has not asked", () => {
    withSessions(ITEMS, 2);
    const html = render();

    // An absent word is no filter at all, so the browse the reader did not ask for still answers
    // the whole history -- and the box opens empty rather than with the string "undefined".
    expect(state.params).toEqual({ page: 0, size: 20, applicationId: undefined, q: undefined });
    expect(html).toContain('value=""');
    expect(html).not.toContain("Clear search");
    expect(html).not.toContain("No interview matches");
    expect(html).toContain("Under_Score Labs");
  });

  it("says which empty it is: nobody spells that word, rather than nobody rehearsed yet", () => {
    state.url = { page: 0, q: "zz" };
    withSessions([], 0);
    const html = render();

    expect(html).toContain("No interview matches “zz”");
    expect(html).toContain(
      "Try a shorter word, or clear the search to see every rehearsal."
    );
    // The escape is the words, not a create form and not the whole history: the reader was looking
    // for one rehearsal, and "pick a target job" would answer a question nobody asked.
    expect(html).toContain("Clear search");
    expect(html).not.toContain("No mock interviews yet");
    expect(html).not.toContain("Pick a target job first");
  });

  it("keeps the card's own empty when the board is narrowed but not searched", () => {
    state.url = { page: 0, application: "app-9" };
    withSessions([], 0);
    const html = render();

    expect(state.params).toEqual({ page: 0, size: 20, applicationId: "app-9", q: undefined });
    // 57.1's shape is unchanged by the box: the card's empty keeps the board's own title and says
    // which list it means in its description, because a card with no rehearsals is not "no
    // interviews ever". Its way out widens the list rather than opening a create form.
    expect(html).toContain("Showing the rehearsals for one application");
    expect(html).toContain("All interviews");
    expect(html).not.toContain("No interview matches");
    expect(html).not.toContain("Pick a target job first");
  });

  it("leaves an unsearched board alone with its own sentence", () => {
    withSessions([], 0);
    const html = render();

    expect(html).toContain("No mock interviews yet");
    expect(html).toContain("Pick a target job first");
    expect(html).not.toContain("No interview matches");
    expect(html).not.toContain("Clear search");
  });

  it("answers the word ahead of the card when both narrow the board", () => {
    // The word is the narrower of the two scopes, and the honest way out is the box: clearing it
    // brings this card's rehearsals back, while widening the card would throw away the words. The
    // chip above the board stays -- the list really is one card's -- but the empty the reader
    // lands on is the one that names the word.
    state.url = { page: 0, application: "app-9", q: "zz" };
    withSessions([], 0);
    const html = render();

    expect(state.params).toEqual({ page: 0, size: 20, applicationId: "app-9", q: "zz" });
    expect(html).toContain("No interview matches “zz”");
    expect(html).toContain("Clear search");
    expect(html).not.toContain("No mock interviews yet");
  });

  it("shows every row the answer carries instead of re-filtering them here", () => {
    // The word lives in the URL, so a pasted `/interviews?q=` link is the same screen rather than
    // the history -- and the board must not narrow the answer a second time. This row spells the
    // word in its company, a column the page does not search, so a client-side filter would drop
    // the rehearsal the reader was looking for.
    state.url = { page: 0, q: "under_score" };
    withSessions([ITEMS[1]], 1);
    const html = render();

    expect(state.params).toEqual({ page: 0, size: 20, applicationId: undefined, q: "under_score" });
    expect(html).toContain('value="under_score"');
    expect(html).toContain("Under_Score Labs");
  });

  it("offers a second page when the server counted more rehearsals than one window holds", () => {
    withSessions(ITEMS, 120);
    const html = render();

    // The number beside the pager is the server's total -- the matches, not the history and not
    // the two rows in hand.
    expect(html).toContain("1–20 of 120 interview sessions");
    expect(html).toContain("Pagination (interview sessions)");
  });

  it("names the words that found nothing in the reader's language", () => {
    state.url = { page: 0, q: "acme" };
    withSessions([], 0);

    expect(render("zh")).toContain("没有与“acme”匹配的面试");
    expect(render("zh")).toContain("清除搜索");
    expect(render("zh")).toContain('placeholder="搜索面试"');
    expect(render("zh")).toContain("按公司、职位或模式搜索面试");
  });
});
