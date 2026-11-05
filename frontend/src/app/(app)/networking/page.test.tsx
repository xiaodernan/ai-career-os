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
  // The page reads a partial URL state: a search nobody made is absent, not `undefined`, and
  // `useUrlState` is the piece SSR cannot hydrate (its adopt-the-query effect runs only in a
  // browser), so each test hands the page the query string it would have adopted.
  url: {} as { q?: string },
  params: undefined as Record<string, unknown> | undefined,
}));

vi.mock("@/lib/hooks/resources", () => ({
  useContacts: (params?: Record<string, unknown>) => {
    state.params = params;
    return state.contacts;
  },
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
 * The registry is the browser's half of 70.3, and it asks the same kind of question the company
 * (58.2) and pipeline (70.2) boards ask: the words in the box are the question the server answered,
 * not a filter over the rows already on screen. Here that distinction is the whole feature, because
 * the route answers a bare list — there is no window for a client-side filter to narrow, so a word
 * that only reached the rows in hand would silently hide everyone the server found instead.
 *
 * Rendered through the real locale provider and the real `ModuleView`, because the copy is the
 * contract: the two empties are different sentences in both shipped languages, and only one of
 * them is allowed to blame the reader's keyboard.
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
    data: { items, total, page: 0, size: items.length },
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
  state.url = {};
  state.params = undefined;
  state.contacts = {
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
    state.url = { q: "ada" };
    withContacts([ITEMS[0]], 1);
    const html = render();

    // The registry is not paged, so the word is the only thing the request carries — and it
    // carries it even when nobody has typed one, which is the difference between asking for
    // `?q=` and asking for a different route.
    expect(state.params).toEqual({ q: "ada" });
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
    expect(state.params).toEqual({ q: undefined });
    expect(html).toContain('value=""');
    expect(html).not.toContain("Clear search");
    expect(html).not.toContain("No contact matches");
    expect(html).toContain("Adareferral Novak");
    expect(html).toContain("Bo Reyes");
  });

  it("says which empty it is: nobody spells that word, rather than nobody saved yet", () => {
    state.url = { q: "zz" };
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
    state.url = { q: "acme" };
    withContacts([], 0);

    expect(render("zh")).toContain("没有与“acme”匹配的联系人");
    expect(render("zh")).toContain("清除搜索");
    expect(render("zh")).toContain('placeholder="搜索联系人"');
    expect(render("zh")).toContain("按姓名、职位、公司或备注搜索联系人");
  });

  it("shows every row the answer carries instead of re-filtering them here", () => {
    // The word lives in the URL, so a pasted `/networking?q=` link is the same screen rather than
    // the browse -- and the board must not narrow the answer a second time. This row's name does
    // not spell the word, and the page has no idea what it does spell (the server read the notes),
    // so a client-side filter would drop a person the reader was looking for.
    state.url = { q: "under_score" };
    withContacts([ITEMS[1]], 1);
    const html = render();

    expect(state.params).toEqual({ q: "under_score" });
    expect(html).toContain('value="under_score"');
    expect(html).toContain("Under_Score Labs");
    expect(html).toContain("Bo Reyes");
  });
});
