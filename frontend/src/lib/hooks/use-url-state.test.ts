import { describe, expect, it } from "vitest";

import { hydrateState } from "@/lib/hooks/use-url-state";

type F = {
  q: string;
  page: number;
  size: number;
  remote?: boolean;
  min_salary?: number;
  max_salary?: number;
};

// Mirrors jobs/page.tsx: DEFAULTS omits the optional filters, but they are declared
// as numeric/boolean keys the panel writes into the URL.
const INITIAL: F = { q: "", page: 0, size: 12 };
const OPTS = {
  numericKeys: ["page", "min_salary", "max_salary", "size"] as (keyof F)[],
  booleanKeys: ["remote"] as (keyof F)[],
};

describe("hydrateState", () => {
  it("restores declared keys that are absent from initial", () => {
    const got = hydrateState(INITIAL, "?remote=1&min_salary=100000&max_salary=200000&page=2", OPTS);
    expect(got).toMatchObject({ page: 2, remote: true, min_salary: 100000, max_salary: 200000 });
    // Numbers must come back typed as numbers, not the raw query strings.
    expect(typeof got.min_salary).toBe("number");
    expect(typeof got.page).toBe("number");
  });

  it("keeps parsing the keys that DO live in initial", () => {
    const got = hydrateState(INITIAL, "?q=go&page=5&size=24", OPTS);
    expect(got).toEqual({ q: "go", page: 5, size: 24 });
  });

  it("parses booleans from 1/true and treats anything else as false", () => {
    expect(hydrateState(INITIAL, "?remote=1", OPTS).remote).toBe(true);
    expect(hydrateState(INITIAL, "?remote=true", OPTS).remote).toBe(true);
    expect(hydrateState(INITIAL, "?remote=0", OPTS).remote).toBe(false);
  });

  it("leaves an absent declared key untouched rather than injecting undefined", () => {
    const got = hydrateState(INITIAL, "?q=rust", OPTS);
    expect("remote" in got).toBe(false);
    expect("min_salary" in got).toBe(false);
    expect(got.q).toBe("rust");
  });

  it("returns the identical initial reference for an empty query string", () => {
    // The hook relies on this identity so its setState bails out of a re-render.
    expect(hydrateState(INITIAL, "", OPTS)).toBe(INITIAL);
    expect(hydrateState(INITIAL, "?", OPTS)).toBe(INITIAL);
  });
});
