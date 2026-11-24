import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import type { Application } from "@/lib/api/types";

const state = vi.hoisted(() => ({
  applications: {
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
  url: {} as { application?: string; q?: string; page: number },
  params: undefined as Record<string, unknown> | undefined,
}));

vi.mock("@/lib/hooks/resources", () => ({
  useApplications: (params?: Record<string, unknown>) => {
    state.params = params;
    return state.applications;
  },
  // The deep link's own read. No test here lands on `?application=`, so the row that would be
  // fetched on its own is simply absent -- the hook must exist because the page calls it.
  useApplication: () => ({ data: undefined }),
}));

vi.mock("@/lib/hooks/actions", () => ({
  useReorderApplication: () => ({ mutate: () => {}, isPending: false }),
}));

// The editor owns every write and mounts a dialog over a form of its own; this board's contract is
// the question it asks, so the test renders the page without it.
vi.mock("@/components/applications/application-dialog", () => ({
  ApplicationDialog: () => null,
}));

vi.mock("@/lib/hooks/use-url-state", () => ({
  useUrlState: () => [state.url, () => {}],
}));

import ApplicationsPage from "./page";
import { LocaleProvider } from "@/lib/i18n/locale-context";

/**
 * The pipeline board is the browser's half of 70.2, and its promise is the same one the company
 * board made in 58.2: the words in the box are the question the server answered, not a filter over
 * the rows already in hand. That matters more here than anywhere else on this screen, because the
 * board is a thing a reader *edits* -- a drag that quietly narrowed the page under it would move a
 * card into a column the request never asked for.
 *
 * Rendered through the real locale provider, the lazily imported kanban's loading fallback
 * and the real pager, because the copy and the count are the contract: the two empties are
 * different sentences in both shipped languages, and the number beside the pager is the
 * server's total rather than this window's length. In production the board only ever renders
 * with client-side data, so the static markup shows the loading fallback, never the cards;
 * the cards themselves are pinned by `components/common/kanban.test.tsx`.
 */

const ITEMS: Application[] = [
  {
    id: "app-1",
    title: "Staff Backend Engineer",
    status: "interview",
    companyName: "Acme Robotics",
    position: 0,
    updatedAt: "2026-11-01T10:00:00Z",
  },
  {
    id: "app-2",
    title: "Data Engineer",
    status: "offer",
    companyName: "Under_Score Labs",
    note: "Referral from Per%cent Events",
    position: 0,
    updatedAt: "2026-11-02T10:00:00Z",
  },
];

const PAGE = readFileSync(fileURLToPath(new URL("./page.tsx", import.meta.url)), "utf8");
const PAGE_HINT_KEYS = ["hintSearch", "hintClearSearch", "hintAdd"];

function buttonMarkup(html: string, text: string): string {
  const label = html.indexOf(`>${text}</button>`);
  const start = html.lastIndexOf("<button", label);
  return html.slice(start, label + text.length + 9);
}

function withApplications(items: Application[], total: number, page = 0): void {
  state.applications = {
    data: { items, total, page, size: 100 },
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
        <ApplicationsPage />
      </LocaleProvider>
    );
  } finally {
    vi.unstubAllGlobals();
  }
}

beforeEach(() => {
  state.url = { page: 0 };
  state.params = undefined;
  state.applications = {
    data: undefined,
    isPending: false,
    isError: false,
    isFetching: false,
    error: null,
    refetch: () => {},
  };
});

describe("the pipeline board", () => {
  it("asks the route for the page and the words together", () => {
    state.url = { page: 2, q: "acme" };
    withApplications(ITEMS, 241, 2);
    const html = render();

    expect(state.params).toEqual({ page: 2, size: 100, q: "acme" });
    // The URL is the whole answer to "what is this board showing", so the box opens with its
    // words: a pasted or reloaded link paints the question and the cards as one state.
    expect(html).toContain('role="search"');
    expect(html).toContain('placeholder="Search applications"');
    expect(html).toContain('aria-label="Search the pipeline by role, company or notes"');
    expect(html).toContain('value="acme"');
    expect(html).toContain("Clear search");
    // The board is dynamically imported (ssr: false): its chunk is not part of the route's
    // first-load Java, and the fallback covers the moment it has not landed. The kanban's
    // own suite renders the board; this page's contract is the query it asks for.
    expect(html).toContain("Loading pipeline");
    expect(html).not.toContain("Staff Backend Engineer");
    // The create form is not displaced by the box: a reader mid-search can still add a card.
    expect(html).toContain("Add</button>");
    // The count is the matches, not the window: page three of 241 at a hundred a page.
    expect(html).toContain("201–241 of 241 applications");
  });

  it("renders no clear button and no q when the reader has not asked", () => {
    withApplications(ITEMS, 2);
    const html = render();

    expect(state.params).toEqual({ page: 0, size: 100, q: undefined });
    expect(html).toContain('value=""');
    expect(html).not.toContain("Clear search");
    // A board shorter than the window it asks for gets no pager at all.
    expect(html).not.toContain("Pagination (applications)");
  });

  it("says which empty it is: no matches, rather than nothing tracked", () => {
    state.url = { page: 0, q: "zz" };
    withApplications([], 0);
    const html = render();

    expect(html).toContain("No application matches “zz”");
    expect(html).toContain("Try a shorter word, or clear the search to see every card in the pipeline.");
    // The escape is the words, not a create form: the pipeline is full, this query is narrow.
    expect(html).toContain("Clear search");
    expect(html).not.toContain("Pipeline is empty");
    expect(html).not.toContain("Add application");
  });

  it("sends an unsearched empty to the create form", () => {
    withApplications([], 0);
    const html = render();

    expect(html).toContain("Pipeline is empty");
    expect(html).toContain("Track a job from its detail page");
    expect(html).toContain("Add application");
    expect(html).not.toContain("No application matches");
    expect(html).not.toContain("Clear search");
  });

  it("names the words that found nothing in the reader's language", () => {
    state.url = { page: 0, q: "acme" };
    withApplications([], 0);

    expect(render("zh")).toContain("没有与“acme”匹配的申请");
    expect(render("zh")).toContain("清除搜索");
    expect(render("zh")).toContain('placeholder="搜索申请"');
  });

  it("pages the matches, so a search over more cards than one window still reaches the rest", () => {
    state.url = { page: 1, q: "acme" };
    withApplications(ITEMS, 141, 1);
    const html = render();

    // 141 matches at a hundred per window is two pages: the total the pager counts is the
    // server's, so the second page of a word is the second page of the matches.
    expect(html).toContain("101–141 of 141 applications");
    expect(state.params).toEqual({ page: 1, size: 100, q: "acme" });
  });
});

describe("the board's primary actions teach their consequences", () => {
  it("puts search, clear and add behind real tooltip triggers", () => {
    state.url = { page: 0, q: "acme" };
    withApplications(ITEMS, 2);
    const html = render();

    for (const label of ["Search", "Clear search", "Add"]) {
      expect(buttonMarkup(html, label), label).toContain('data-slot="tooltip-trigger"');
    }
  });

  it("teaches the action on each empty state as well", () => {
    withApplications([], 0);
    expect(buttonMarkup(render(), "Add application")).toContain('data-slot="tooltip-trigger"');

    state.url = { page: 0, q: "missing" };
    expect(buttonMarkup(render(), "Clear search")).toContain('data-slot="tooltip-trigger"');
  });

  it("keeps the same trigger count in Chinese and resolves every sentence from the tables", () => {
    const en = readFileSync(
      fileURLToPath(new URL("../../../lib/i18n/en.ts", import.meta.url)),
      "utf8",
    );
    const zh = readFileSync(
      fileURLToPath(new URL("../../../lib/i18n/zh.ts", import.meta.url)),
      "utf8",
    );
    const triggers = (html: string) => html.match(/data-slot="tooltip-trigger"/g)?.length ?? 0;

    expect(triggers(render("zh"))).toBe(triggers(render("en")));
    for (const key of PAGE_HINT_KEYS) {
      expect(PAGE).toContain(`t("applications.${key}")`);
      expect(en).toContain(`${key}:`);
      expect(zh).toContain(`${key}:`);
    }
    const wired = PAGE.match(/applications\.hint\w+/g) ?? [];
    expect(new Set(wired).size).toBe(PAGE_HINT_KEYS.length);
    expect(PAGE).not.toMatch(/label="[A-Z][a-z]+ [a-z]/);
  });
});
