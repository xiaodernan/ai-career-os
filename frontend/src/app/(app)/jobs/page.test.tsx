import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

const state = vi.hoisted(() => ({
  jobs: {
    data: undefined as
      | { items: unknown[]; total: number; page: number; size: number }
      | undefined,
    isPending: false,
    isError: false,
    isFetching: false,
    error: null as unknown,
    refetch: () => {},
  },
  saved: {
    data: { items: [], total: 0, page: 0, size: 50 },
    isPending: false,
    isError: false,
    isFetching: false,
    error: null as unknown,
    refetch: () => {},
  },
  // The page reads a partial URL state: a filter nobody set is absent, not `undefined`.
  url: { page: 0, size: 12 } as Record<string, unknown>,
}));

vi.mock("@/lib/hooks/use-url-state", () => ({
  useUrlState: () => [state.url, () => {}],
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: () => undefined }),
}));

// Only the hooks this tree reads are stood in for; every other export keeps its real
// definition so a module the page imports cannot die of a missing name.
vi.mock("@/lib/hooks/resources", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/hooks/resources")>()),
  useJobs: () => state.jobs,
  useSavedJobs: () => state.saved,
  useResumes: () => ({ data: { items: [] } }),
  useResume: () => ({ data: undefined }),
  useSavedSearches: () => ({ data: { items: [] } }),
}));

vi.mock("@/lib/hooks/actions", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/hooks/actions")>()),
  useToggleSaveJob: () => ({ mutate: () => undefined, isPending: false }),
  useCreateSavedSearch: () => ({ mutate: () => undefined, isPending: false }),
  useDeleteSavedSearch: () => ({ mutate: () => undefined, isPending: false }),
  useImportJob: () => ({ mutate: () => undefined, isPending: false }),
  useAnalyzeJd: () => ({ mutate: () => undefined, isPending: false }),
  useResumeSuggestions: () => ({ mutate: () => undefined, isPending: false }),
  useStoredJd: () => ({ data: null, isError: false }),
}));

import JobsPage from "./page";
import { LocaleProvider } from "@/lib/i18n/locale-context";

/**
 * The board's empty state has two jobs: tell a reader with filters on why the list is
 * short, and tell a reader with an empty board the truth. The second one regressed into
 * the first: a brand-new account with no filter set was told "No roles match these
 * filters yet" beside a `Clear filters` button that had nothing to clear.
 *
 * Rendered through the real locale provider over the real page component: the assertions
 * are the sentences a reader sees, not the keys a mock would hand back.
 */

function render(locale: "en" | "zh" = "en"): string {
  vi.stubGlobal("window", {
    localStorage: { getItem: () => locale, setItem: () => {} },
  });
  try {
    return renderToStaticMarkup(
      <LocaleProvider>
        <JobsPage />
      </LocaleProvider>
    );
  } finally {
    vi.unstubAllGlobals();
  }
}

function withEmptyBoard(): void {
  state.jobs.data = { items: [], total: 0, page: 0, size: 12 };
}

beforeEach(() => {
  state.url = { page: 0, size: 12 };
  withEmptyBoard();
});

describe("JobsPage empty Discover board", () => {
  it("does not blame filters for an empty board when no filter is set", () => {
    const html = render("en");

    expect(html).toContain("The job board is empty");
    expect(html).not.toContain("No roles match these filters yet.");
    expect(html).not.toContain("Clear filters");
    expect(html).toContain('href="/copilot"');
  });

  it("names the filters when one is what emptied the board", () => {
    state.url = { q: "rust", page: 0, size: 12 };

    const html = render("en");

    expect(html).toContain("No roles match these filters yet.");
    expect(html).toContain("Clear filters");
    expect(html).not.toContain("The job board is empty");
  });

  it("speaks the reader's language on an empty board", () => {
    const html = render("zh");

    expect(html).toContain("职位板还空着");
    expect(html).not.toContain("目前没有职位符合这些筛选");
  });
});
