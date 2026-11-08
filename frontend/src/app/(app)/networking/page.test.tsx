import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import type { Contact } from "@/lib/api/types";

const state = vi.hoisted(() => ({
  contacts: {
    data: undefined as
      | { items: unknown[]; total: number; page: number; size: number }
      | undefined,
    isPending: false,
    isError: false,
    isFetching: false,
    error: null as unknown,
    refetch: () => {},
  },
  relations: {
    data: undefined as { relation: string; count: number }[] | undefined,
    isPending: false,
    isError: false,
    isFetching: false,
    error: null as unknown,
    refetch: () => {},
  },
  // The page reads a partial URL state: a search nobody made is absent, not `undefined`, and
  // `useUrlState` is the piece SSR cannot hydrate (its adopt-the-query effect runs only in a
  // browser), so each test hands the page the query string it would have adopted.
  url: {} as { page: number; q?: string; relation?: string },
  params: undefined as Record<string, unknown> | undefined,
}));

vi.mock("@/lib/hooks/resources", () => ({
  useContacts: (params?: Record<string, unknown>) => {
    state.params = params;
    return state.contacts;
  },
  useContactRelations: () => state.relations,
}));

// The registry's own writes and the outreach draft. The dialog at the bottom of the page calls the
// three mutation hooks when it mounts, and the draft card is only rendered once a draft exists, so
// both are stubs here rather than the QueryClient they would need.
vi.mock("@/lib/hooks/actions", () => ({
  useCreateContact: () => ({ mutate: () => {}, isPending: false }),
  useUpdateContact: () => ({ mutate: () => {}, isPending: false }),
  useDeleteContact: () => ({ mutate: () => {}, isPending: false }),
}));

vi.mock("@/lib/hooks/growth", () => ({
  useOutreachDraft: () => ({ data: undefined, isPending: false, mutate: () => {} }),
}));

vi.mock("@/lib/hooks/use-url-state", () => ({
  useUrlState: () => [state.url, () => {}],
}));

import NetworkingPage from "./page";
import { LocaleProvider } from "@/lib/i18n/locale-context";

/**
 * The registry is the browser's half of 70.3, and since 72.1 also of the server's window: the
 * words in the box are the question the server answered, not a filter over the rows already on
 * screen, and the rows are one page of that answer. A client-side filter would silently hide
 * everyone the server found on another page. Rendered through the real locale provider, the real
 * ModuleView and the real pager, so the count beside it is the server's total rather than the
 * length of the rows in hand.
 */

const ITEMS: Contact[] = [
  { id: "ct-1", name: "Adareferral Novak", role: "Staff Engineer", company: "Acme Robotics" },
  {
    id: "ct-2",
    name: "Bo Reyes",
    role: "Recruiter",
    company: "Under_Score Labs",
    relation: "referrer",
    lastTouchAt: "2026-10-01T00:00:00Z",
  },
];

function withContacts(items: Contact[], total: number): void {
  state.contacts = {
    // 72.1: the window is the server's, not a page the client invented over a bare list.
    data: { items, total, page: 0, size: 50 },
    isPending: false,
    isError: false,
    isFetching: false,
    error: null,
    refetch: () => {},
  };
}

function withRelations(relations: { relation: string; count: number }[]): void {
  state.relations = {
    data: relations,
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
        <NetworkingPage />
      </LocaleProvider>
    );
  } finally {
    vi.unstubAllGlobals();
  }
}

beforeEach(() => {
  state.url = { page: 0 };
  state.params = undefined;
  state.contacts = {
    data: undefined,
    isPending: false,
    isError: false,
    isFetching: false,
    error: null,
    refetch: () => {},
  };
  state.relations = {
    data: undefined,
    isPending: false,
    isError: false,
    isFetching: false,
    error: null,
    refetch: () => {},
  };
});

describe("the contacts registry", () => {
  it("asks the route for the word in the box, and shows it back", () => {
    state.url = { page: 0, q: "ada" };
    withContacts([ITEMS[0]], 1);
    const html = render();

    // The word travels beside the window the board asks with — and it carries `q` even when
    // nobody has typed one, which is the difference between asking for `?q=` and a different route.
    expect(state.params).toEqual({ page: 0, q: "ada", relation: undefined, size: 50 });
    expect(html).toContain('role="search"');
    expect(html).toContain('placeholder="Search contacts"');
    expect(html).toContain('aria-label="Search the registry by name, role, company or notes"');
    expect(html).toContain('value="ada"');
    expect(html).toContain("Clear search");
    expect(html).toContain("Adareferral Novak");
    // The box does not displace the row's own actions: a reader mid-search can still draft for
    // the person they found, which is the point of the registry.
    expect(html).toContain(">Draft</button>");
    expect(html).toContain("Add contact");
  });

  it("renders no clear button and no question when the reader has not asked", () => {
    withContacts(ITEMS, 2);
    const html = render();

    // An absent word is no filter at all, so the browse the reader did not ask for still answers
    // the whole registry — and the box opens empty rather than with the string "undefined".
    expect(state.params).toEqual({ page: 0, q: undefined, relation: undefined, size: 50 });
    expect(html).toContain('value=""');
    expect(html).not.toContain("Clear search");
    expect(html).not.toContain("No contact matches");
    expect(html).toContain("Adareferral Novak");
    expect(html).toContain("Bo Reyes");
  });

  it("says which empty it is: nobody spells that word, rather than nobody saved yet", () => {
    state.url = { page: 0, q: "zz" };
    withContacts([], 0);
    const html = render();

    expect(html).toContain("No contact matches “zz”");
    expect(html).toContain(
      "Try a shorter word, or clear the search to see everyone in the registry."
    );
    // The escape is the words, not a create form: the registry is full, this query is narrow, and
    // a reader who was looking for Bo does not want to add someone.
    expect(html).toContain("Clear search");
    expect(html).not.toContain("No contacts yet");
  });

  it("leaves an unsearched empty alone with its own sentence", () => {
    withContacts([], 0);
    const html = render();

    expect(html).toContain("No contacts yet");
    expect(html).toContain("Add the referrers, mentors and peers you talk to");
    expect(html).not.toContain("No contact matches");
    expect(html).not.toContain("Clear search");
  });

  it("names the words that found nothing in the reader's language", () => {
    state.url = { page: 0, q: "acme" };
    withContacts([], 0);

    expect(render("zh")).toContain("没有与“acme”匹配的联系人");
    expect(render("zh")).toContain("清除搜索");
    expect(render("zh")).toContain('placeholder="搜索联系人"');
    expect(render("zh")).toContain("按姓名、职位、公司或备注搜索联系人");
  });

  it("shows every row the answer carries instead of re-filtering them here", () => {
    // The word lives in the URL, so a pasted `/networking?q=` link is the same screen rather than
    // the browse — and the board must not narrow the answer a second time. This row's name does
    // not spell the word, and the page has no idea what it does spell (the server read the notes),
    // so a client-side filter would drop a person the reader was looking for.
    state.url = { page: 0, q: "under_score" };
    withContacts([ITEMS[1]], 1);
    const html = render();

    expect(state.params).toEqual({ page: 0, q: "under_score", relation: undefined, size: 50 });
    expect(html).toContain('value="under_score"');
    expect(html).toContain("Under_Score Labs");
    expect(html).toContain("Bo Reyes");
  });

  it("offers a second page when the server counted more people than one window holds", () => {
    state.url = { page: 0 };
    withContacts(ITEMS, 120);
    const html = render();

    expect(state.params).toEqual({ page: 0, q: undefined, relation: undefined, size: 50 });
    // The number beside the pager is the server's total, not the two rows in hand: a client-made
    // envelope over a bare list would have said "1-2 of 2" and offered no second page at all.
    expect(html).toContain("1–50 of 120 Contacts");
    expect(html).toContain("Pagination (Contacts)");
  });

  it("restores the pasted page and hides the pager when everything fits", () => {
    state.url = { page: 2, q: "ada" };
    withContacts([ITEMS[0]], 1);
    const html = render();

    expect(state.params).toEqual({ page: 2, q: "ada", relation: undefined, size: 50 });
    expect(html).not.toContain("Pagination (");
  });

  it("renders the relation chips from the registry's own vocabulary", () => {
    withRelations([
      { relation: "referrer", count: 3 },
      { relation: "mentor", count: 1 },
    ]);
    withContacts(ITEMS, 4);
    const html = render();

    // The counts are the server's, not a count of the rows in hand.
    expect(html).toContain('aria-label="Narrow the registry by relation"');
    expect(html).toContain("All relations");
    expect(html).toContain("referrer");
    expect(html).toContain(">3<");
    expect(html).toContain("mentor");
    expect(html).toContain(">1<");
  });

  it("narrows the registry by the relation chip and carries it in the request", () => {
    state.url = { page: 0, relation: "referrer" };
    withRelations([{ relation: "referrer", count: 1 }]);
    withContacts([ITEMS[1]], 1);
    const html = render();

    // The chip travels beside the word; the server does the narrowing.
    expect(state.params).toEqual({ page: 0, q: undefined, relation: "referrer", size: 50 });
    expect(html).toContain('aria-pressed="true"');
    expect(html).toContain("Bo Reyes");
  });

  it("keeps the word and the chip together on one request", () => {
    state.url = { page: 0, q: "ada", relation: "referrer" };
    withRelations([{ relation: "referrer", count: 1 }]);
    withContacts([ITEMS[0]], 1);
    const html = render();

    expect(state.params).toEqual({ page: 0, q: "ada", relation: "referrer", size: 50 });
    expect(html).toContain("Adareferral Novak");
    expect(html).toContain('aria-pressed="true"');
  });

  it("resets the window when the reader taps a different relation", () => {
    state.url = { page: 2, relation: "referrer" };
    withRelations([{ relation: "referrer", count: 120 }]);
    withContacts(ITEMS, 120);
    const html = render();

    // The pasted page stays in the URL; the narrowing is the server's answer to it.
    expect(state.params).toEqual({ page: 2, q: undefined, relation: "referrer", size: 50 });
    expect(html).toContain('aria-pressed="true"');
  });

  it("says which narrowing left the registry empty — by relation, not by word", () => {
    state.url = { page: 0, relation: "mentor" };
    withContacts([], 0);
    const html = render();

    expect(html).toContain("“mentor”");
    expect(html).toContain("Clear search");
    expect(html).not.toContain("No contacts yet");
  });
});
