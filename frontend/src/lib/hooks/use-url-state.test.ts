import { describe, expect, it } from "vitest";

import { serializeJobFilters } from "@/lib/api/normalize";
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

  it("adopts an optional key whose initial value is undefined", () => {
    // `/knowledge?src=` is declared this way (`{ src: undefined }`, no numeric or boolean keys at all),
    // so the parameter can only ever come from the URL: a reader that skipped a key because its default
    // holds `undefined` would lose the citation's deep link on every reload, and nothing else here would
    // notice, since every other fixture's keys carry a value.
    const FOCUS = { src: undefined as string | undefined };
    expect(hydrateState(FOCUS, "?src=6f1c0b3e-0000-4000-8000-000000000007")).toEqual({
      src: "6f1c0b3e-0000-4000-8000-000000000007",
    });
    // A key nobody declared is still not adopted, or any query string would become state.
    expect("other" in hydrateState(FOCUS, "?other=1")).toBe(false);
    // And `?src=` with nothing after it comes back as the empty string: the hook does not invent a
    // default, so it is the caller that turns a blank into "no filter" (`state.src || undefined`).
    expect(hydrateState(FOCUS, "?src=")).toEqual({ src: "" });
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

  it("drops a numeric value the request layer cannot bind", () => {
    // Every one of these used to land in state as a number: NaN for the two
    // unparseable ones, Infinity for the overflow, 0 for the empty values.
    const got = hydrateState(INITIAL, "?size=abc&page=1e999&min_salary=many", OPTS);
    expect(got).toEqual({ q: "", page: 0, size: 12 });
    expect("min_salary" in got).toBe(false);
  });

  it("reads an empty value as absent, not as zero", () => {
    // `?size=&page=` is what a half-typed or hand-edited link looks like. Number("")
    // is 0, which serialized to a one-row page and made the pager disagree with it.
    const got = hydrateState(INITIAL, "?size=&page=", OPTS);
    expect(got).toEqual({ q: "", page: 0, size: 12 });
    // Whitespace-only is the same trap wearing a disguise: Number("  ") is 0 too.
    expect(hydrateState(INITIAL, "?size=%20%20", OPTS).size).toBe(12);
  });

  it("normalises whitespace but will not invent a fractional window", () => {
    expect(hydrateState(INITIAL, "?size=%2024%20", OPTS).size).toBe(24);
    // The backend binds these parameters as int, so "12.5" would 400 the request.
    expect(hydrateState(INITIAL, "?size=12.5", OPTS).size).toBe(12);
    expect(hydrateState(INITIAL, "?page=3.0", OPTS).page).toBe(3);
  });

  it("accepts a negative page, whose floor is the server's to enforce", () => {
    // Paging clamps it and PageDTO reports the window actually served, so the pager
    // corrects itself — the URL only has to carry something bindable.
    expect(hydrateState(INITIAL, "?page=-3", OPTS).page).toBe(-3);
  });

  it("hands the serializer the default window, not size=NaN", () => {
    // The consequence that matters: whatever hydrateState adopts is written back
    // into the address bar by update() and put on the wire verbatim by buildUrl,
    // so a poison number here is sticky across reloads.
    const wire = serializeJobFilters(hydrateState(INITIAL, "?size=abc&page=NaN", OPTS));
    expect(wire).toEqual({ page: 0, size: 12 });
    for (const v of Object.values(wire)) {
      expect(typeof v === "number" && Number.isFinite(v)).toBe(true);
    }
  });
});
