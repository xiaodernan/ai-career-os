import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import type { LetterCatalogItem } from "@/lib/api/types";

const state = vi.hoisted(() => ({
  letters: {
    data: undefined as { items: LetterCatalogItem[]; total: number } | undefined,
    isPending: false,
    isError: false,
    error: null as unknown,
    isFetching: false,
    refetch: () => {},
  },
  url: { q: undefined as string | undefined },
  written: undefined as Record<string, unknown> | undefined,
}));

vi.mock("@/lib/hooks/letters", () => ({
  useLetters: () => state.letters,
}));

vi.mock("@/lib/hooks/use-url-state", () => ({
  useUrlState: () => [
    state.url,
    (patch: Record<string, unknown>) => {
      state.written = patch;
    },
  ],
}));

import LettersPage from "./page";
import { LocaleProvider } from "@/lib/i18n/locale-context";

const ITEMS: LetterCatalogItem[] = [
  {
    id: "l-1",
    applicationId: "app-1",
    applicationTitle: "Backend Engineer",
    companyName: "Acme",
    tone: "confident",
    length: "standard",
    body: "Dear Acme, I have read your post-mortems because I keep my own incident reviews.",
    createdAt: "2026-11-10T09:00:00Z",
    updatedAt: "2026-11-10T09:00:00Z",
  },
  {
    id: "l-2",
    applicationId: "app-2",
    applicationTitle: "Staff Engineer",
    companyName: "Globex",
    body: "Dear Globex, the registry and the edge here are the same lesson I already know.",
    createdAt: "2026-11-11T09:00:00Z",
    updatedAt: "2026-11-11T09:00:00Z",
  },
];

beforeEach(() => {
  state.letters = {
    data: undefined,
    isPending: false,
    isError: false,
    error: null,
    isFetching: false,
    refetch: () => {},
  };
  state.url = { q: undefined };
  state.written = undefined;
});

function render(locale: "en" | "zh" = "en"): string {
  vi.stubGlobal("window", {
    localStorage: { getItem: () => locale, setItem: () => {} },
  });
  try {
    return renderToStaticMarkup(
      <LocaleProvider>
         <LettersPage />
      </LocaleProvider>,
    );
  } finally {
    vi.unstubAllGlobals();
  }
}

describe("the letters page", () => {
  it("renders each kept letter with its application and company", () => {
    state.letters = {
      data: { items: ITEMS, total: 2 },
      isPending: false,
      isError: false,
      error: null,
      isFetching: false,
      refetch: () => {},
    };

    const html = render();

    expect(html).toContain("Backend Engineer");
    expect(html).toContain("Acme");
    expect(html).toContain("incident reviews");
    expect(html).toContain("Staff Engineer");
    expect(html).toContain("Globex");
  });

  it("speaks an honest empty composer when the shelf is empty", () => {
    state.letters = {
      data: { items: [], total: 0 },
      isPending: false,
      isError: false,
      error: null,
      isFetching: false,
      refetch: () => {},
    };

    const html = render();

    expect(html).toContain("Nothing kept yet");
    expect(html).toContain("the moment a draft earns its place");
  });

  it("narrows to the letters matching the words and says so out loud", () => {
    state.url = { q: "ackme" }; // intentional typo: no match
    state.letters = {
      data: { items: ITEMS, total: 2 },
      isPending: false,
      isError: false,
      error: null,
      isFetching: false,
      refetch: () => {},
    };

    const html = render();

    expect(html).toContain("No letter matches");
    expect(html).not.toContain("incident reviews");
  });

  it("renders the count of what is on screen", () => {
    state.url = { q: "globex" };
    state.letters = {
      data: { items: ITEMS, total: 2 },
      isPending: false,
      isError: false,
      error: null,
      isFetching: false,
      refetch: () => {},
    };

    const html = render();

    expect(html).toContain("1 letters kept");
    expect(html).not.toContain("incident reviews");
    expect(html).toContain("registry and the edge");
  });

  it("waits honestly with an announced status while the letters load", () => {
    state.letters = {
      data: undefined,
      isPending: true,
      isError: false,
      error: null,
      isFetching: true,
      refetch: () => {},
    };

    const html = render();

    expect(html).toContain('role="status"');
    expect(html).not.toContain("Nothing kept yet");
  });
});
