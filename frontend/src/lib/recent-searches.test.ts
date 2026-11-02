import { describe, expect, it } from "vitest";

import { RECENT_SEARCH_LIMIT, loadRecentSearches, rememberSearch } from "./recent-searches";

/** The smallest thing that behaves like localStorage, so no browser is needed. */
function fakeStorage(initial: Record<string, string> = {}) {
  const data = { ...initial };
  return {
    data,
    getItem: (key: string) => data[key] ?? null,
    setItem: (key: string, value: string) => {
      data[key] = value;
    },
  };
}

describe("recent searches", () => {
  it("answers nothing where there is no browser", () => {
    expect(loadRecentSearches(undefined)).toEqual([]);
    expect(rememberSearch("kafka", undefined)).toEqual([]);
  });

  it("puts the newest query first", () => {
    const store = fakeStorage();
    rememberSearch("kafka", store);
    rememberSearch("postgres", store);

    expect(loadRecentSearches(store)).toEqual(["postgres", "kafka"]);
  });

  it("moves a repeated query up instead of storing it twice", () => {
    const store = fakeStorage();
    rememberSearch("kafka", store);
    rememberSearch("postgres", store);
    rememberSearch("  KAFKA  ", store);

    expect(loadRecentSearches(store)).toEqual(["KAFKA", "postgres"]);
  });

  it("ignores a query too short for the palette to search", () => {
    const store = fakeStorage();

    expect(rememberSearch(" k ", store)).toEqual([]);
    expect(store.data).toEqual({});
  });

  it("keeps only the latest few", () => {
    const store = fakeStorage();
    for (const term of ["one1", "two2", "three3", "four4", "five5", "six6"]) {
      rememberSearch(term, store);
    }

    const kept = loadRecentSearches(store);
    expect(kept).toHaveLength(RECENT_SEARCH_LIMIT);
    expect(kept[0]).toBe("six6");
    expect(kept).not.toContain("one1");
  });

  it("survives a value that is not the list it wrote", () => {
    expect(loadRecentSearches(fakeStorage({ "careeros.recent-searches": "{oops" }))).toEqual([]);
    expect(loadRecentSearches(fakeStorage({ "careeros.recent-searches": '{"a":1}' }))).toEqual([]);
  });
});
