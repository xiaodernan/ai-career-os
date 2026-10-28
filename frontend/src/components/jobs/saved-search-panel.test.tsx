import { describe, expect, it, vi } from "vitest";
import * as React from "react";
import { renderToStaticMarkup } from "react-dom/server";

// The identity translator keeps the panel's keys visible in the markup: the
// holes are appended so an aria-label can show which name it was built for.
vi.mock("@/lib/i18n/locale-context", () => ({
  useLocale: () => ({
    locale: "en",
    t: (key: string, vars?: Record<string, unknown>) =>
      vars ? `${key}|${Object.values(vars).join(",")}` : key,
    setLocale: () => {},
  }),
}));

const state = vi.hoisted(() => ({
  searches: [] as { id: string; name: string; criteria: Record<string, unknown> }[],
  loaded: true,
}));

vi.mock("@/lib/hooks/resources", () => ({
  useSavedSearches: () => ({ data: state.loaded ? state.searches : undefined, isSuccess: state.loaded }),
}));

vi.mock("@/lib/hooks/actions", () => ({
  useCreateSavedSearch: () => ({ mutate: () => {}, isPending: false, reset: () => {} }),
  useDeleteSavedSearch: () => ({ mutate: () => {}, isPending: false }),
}));

import { SavedSearchPanel } from "./saved-search-panel";

/**
 * The saved-search panel is mostly a list and a button, but two of its states
 * are promises the server also keeps: an empty board cannot be saved (the
 * button is disabled, not hidden, so the reason stays on screen), and the
 * empty copy speaks only once the list has actually answered -- a flash of
 * "No saved searches yet" over a list that is about to arrive would be a lie
 * the page tells every visit.
 */

function render(value: { q?: string; location?: string; remote?: boolean }): string {
  return renderToStaticMarkup(
    <SavedSearchPanel value={value} onApply={() => {}} />
  );
}

describe("SavedSearchPanel", () => {
  it("disables saving when the board is browsing without a question", () => {
    state.searches = [];
    const html = render({});
    expect(html).toContain("savedSearches.saveAction");
    // The attribute, not the class string: the button's own classes mention
    // `disabled:` states, so a looser match would pass on an enabled button.
    expect(html).toMatch(/<button[^>]*\sdisabled=""/);
    expect(html).toContain("savedSearches.empty");
  });

  it("enables saving once a filter is active", () => {
    state.searches = [];
    const html = render({ q: "java" });
    expect(html).not.toMatch(/<button[^>]*\sdisabled=""/);
  });

  it("lists saved searches and names the one a delete would remove", () => {
    state.searches = [
      { id: "ss-1", name: "Java in Shanghai", criteria: { q: "java", location: "Shanghai" } },
      { id: "ss-2", name: "Remote only", criteria: { remote: true } },
    ];
    const html = render({ q: "java" });
    expect(html).toContain("Java in Shanghai");
    expect(html).toContain("Remote only");
    expect(html).toContain("savedSearches.deleteAria|Java in Shanghai");
    expect(html).not.toContain("savedSearches.empty");
  });

  it("holds the empty copy until the list has answered", () => {
    state.searches = [];
    state.loaded = false;
    const html = render({ q: "java" });
    expect(html).not.toContain("savedSearches.empty");
    state.loaded = true;
  });
});
