import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import type { Company } from "@/lib/api/types";

const state = vi.hoisted(() => ({
  companies: {
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
  url: {} as { q?: string; page: number },
  params: undefined as Record<string, unknown> | undefined,
}));

vi.mock("@/lib/hooks/resources", () => ({
  useCompanies: (params?: Record<string, unknown>) => {
    state.params = params;
    return state.companies;
  },
}));

vi.mock("@/lib/hooks/use-url-state", () => ({
  useUrlState: () => [state.url, () => {}],
}));

import CompaniesPage from "./page";
import { LocaleProvider } from "@/lib/i18n/locale-context";

/**
 * The companies board is the browser's half of 58.2, and its promise is that the words in the
 * box are the question the server answered: the screen asks `?q=` rather than filtering the
 * window it already has, so the rows under the box and the number beside it describe the same
 * set -- and a search that found nothing says so instead of claiming nobody has researched a
 * company yet.
 *
 * Rendered through the real locale provider over the real page component, because the copy is
 * the contract: the two empties are different sentences in both shipped languages.
 */

const ITEMS: Company[] = [
  {
    id: "co-1",
    name: "Acme Robotics",
    industry: "ai",
    size: "50-200",
    website: "https://acme.test",
    techStack: ["python", "ros"],
    openRoleCount: 3,
  },
  { id: "co-2", name: "Under_Score Labs", website: "javascript:alert(1)" },
];

function withCompanies(items: Company[], total: number, page = 0): void {
  state.companies = {
    data: { items, total, page, size: 20 },
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
        <CompaniesPage />
      </LocaleProvider>
    );
  } finally {
    vi.unstubAllGlobals();
  }
}

beforeEach(() => {
  state.url = { page: 0 };
  state.params = undefined;
  state.companies = {
    data: undefined,
    isPending: false,
    isError: false,
    isFetching: false,
    error: null,
    refetch: () => {},
  };
});

describe("the companies board", () => {
  it("asks the route for the page and the words together", () => {
    state.url = { page: 2, q: "acme" };
    withCompanies(ITEMS, 41, 2);
    const html = render();

    expect(state.params).toEqual({ page: 2, size: 20, q: "acme" });
    // The URL is the whole answer to "what is this list showing", so the box opens with its
    // words: a pasted or reloaded link paints the question and the rows as one state.
    expect(html).toContain('role="search"');
    expect(html).toContain('placeholder="Search companies"');
    expect(html).toContain('aria-label="Search companies by name"');
    expect(html).toContain('value="acme"');
    expect(html).toContain("Clear search");
    expect(html).toContain("Acme Robotics");
    expect(html).toContain("Under_Score Labs");
    // A stored website that cannot be a link is not offered as one (#31's rule, asserted here on
    // the row this board renders).
    expect(html).not.toContain('href="javascript:alert(1)"');
    expect(html).toContain("3 roles");
    // A page in the middle of a match list is still a page: the pager reads the answer's index
    // and the server's total, so the last window says what the last window holds.
    expect(html).toContain("41–41 of 41 companies");
  });

  it("renders no clear button and no q when the reader has not asked", () => {
    withCompanies(ITEMS, 2);
    const html = render();

    expect(state.params).toEqual({ page: 0, size: 20, q: undefined });
    expect(html).toContain('value=""');
    expect(html).not.toContain("Clear search");
    // A board shorter than the window it asks for gets no pager at all.
    expect(html).not.toContain("Pagination (companies)");
  });

  it("says which empty it is: no matches, rather than nothing researched", () => {
    state.url = { page: 0, q: "zz" };
    withCompanies([], 0);
    const html = render();

    expect(html).toContain("No company matches “zz”");
    expect(html).toContain("Try a shorter word, or clear the search to see every company.");
    // The escape is the words, not a research prompt: the catalog is full, this query is narrow.
    expect(html).toContain("Clear search");
    expect(html).not.toContain("No companies researched");
    expect(html).not.toContain('href="/copilot"');
  });

  it("sends an unsearched empty to research a company", () => {
    withCompanies([], 0);
    const html = render();

    expect(html).toContain("No companies researched");
    expect(html).toContain("The research agent builds company profiles");
    expect(html).toContain('href="/copilot"');
    expect(html).not.toContain("No company matches");
    expect(html).not.toContain("Clear search");
  });

  it("names the words that found nothing in the reader's language", () => {
    state.url = { page: 0, q: "acme" };
    withCompanies([], 0);

    expect(render("zh")).toContain("没有与“acme”匹配的公司");
    expect(render("zh")).toContain("清除搜索");
  });

  it("pages the matches, so a search over more rows than one window still reaches the rest", () => {
    state.url = { page: 1, q: "acme" };
    withCompanies(ITEMS, 41, 1);
    const html = render();

    // 41 matches at 20 per window is three pages: the count is the server's total, not the
    // length of the slice this page happens to hold.
    expect(html).toContain("41 companies");
    expect(state.params).toEqual({ page: 1, size: 20, q: "acme" });
  });
});
