import { describe, expect, it } from "vitest";

import {
  MAP_SECTIONS,
  lenientJson,
  listText,
  mapRows,
  rawMap,
  readString,
  readYears,
  rowsToMap,
  type MapRow,
} from "@/lib/profile-maps";

/**
 * The career-profile editor's data contract, extracted from
 * `components/settings/profile-cards.tsx`. What it holds that a render test cannot:
 * a typed value's survival through the render → edit → save cycle. On screen a
 * string that looks like JSON and a JSON value are the same characters, so the
 * round trip only a test can watch is the map → rows → map one the free-form
 * card performs on every save.
 */

const row = (key: string, value: string): MapRow => ({ key, value });

describe("mapRows → rowsToMap: the typed round trip", () => {
  it("a string value survives as a string", () => {
    // A URL is the common case, and JSON.parse("https://…") throws — so it stays text.
    const rows = mapRows({ links: { github: "https://github.com/a" } }, "links");
    expect(rows).toEqual([row("github", "https://github.com/a")]);
    expect(rowsToMap(rows)).toEqual({ github: "https://github.com/a" });
  });

  it("a stored object survives as an object, not as its spelling", () => {
    const rows = mapRows({ preferences: { remote: { days: 2, ok: true } } }, "preferences");
    expect(rows).toEqual([row("remote", '{"days":2,"ok":true}')]);
    expect(rowsToMap(rows)).toEqual({ remote: { days: 2, ok: true } });
  });

  it("numbers and booleans come back as numbers and booleans", () => {
    // The env-var behaviour the card documents: a value that parses keeps its type.
    expect(rowsToMap([row("a", "12")])).toEqual({ a: 12 });
    expect(rowsToMap([row("b", "true")])).toEqual({ b: true });
    expect(rowsToMap([row("c", "null")])).toEqual({ c: null });
    expect(rowsToMap([row("d", '"quoted"')])).toEqual({ d: "quoted" });
  });

  it("a value that does not parse stays exactly what was typed", () => {
    expect(rowsToMap([row("e", "mostly fine")])).toEqual({ e: "mostly fine" });
    expect(lenientJson("{broken:")).toBe("{broken:");
    expect(lenientJson("")).toBe("");
  });

  it("a row with a blank key is not saved", () => {
    expect(rowsToMap([row("", "value"), row("   ", "value"), row("real", "ok")]))
        .toEqual({ real: "ok" });
  });

  it("an editor that emptied every row saves the map as the clear", () => {
    // The PATCH replaces wholesale, so {} is how a map gets emptied — not omitted.
    expect(rowsToMap([])).toEqual({});
    expect(rowsToMap([row("", "")])).toEqual({});
  });

  it("nested JSON keeps its order and depth", () => {
    const stored = { a: { b: [1, 2, { c: "d" }] } };
    expect(rowsToMap(mapRows({ links: stored }, "links"))).toEqual({ a: { b: [1, 2, { c: "d" }] } });
  });
});

describe("rawMap: only an object reads as a map", () => {
  it("reads an object and rejects an array, a string and a missing key", () => {
    expect(rawMap({ links: { a: 1 } }, "links")).toEqual({ a: 1 });
    expect(rawMap({ links: [1, 2] }, "links")).toEqual({});
    expect(rawMap({ links: "nope" }, "links")).toEqual({});
    expect(rawMap({}, "links")).toEqual({});
    expect(rawMap(null, "links")).toEqual({});
  });

  it("mapRows of a non-object is no rows, not a crash", () => {
    expect(mapRows({ links: [1, 2] }, "links")).toEqual([]);
  });
});

describe("the three sections", () => {
  it("are exactly the three maps the PATCH replaces", () => {
    expect(MAP_SECTIONS.map((s) => s.name)).toEqual(["links", "workAuthorization", "preferences"]);
  });
});

describe("the career-profile readers", () => {
  it("listText joins an array and reads anything else as nothing", () => {
    expect(listText(["backend", "ai"])).toBe("backend, ai");
    expect(listText("backend")).toBe("");
    expect(listText(null)).toBe("");
  });

  it("readString returns strings only", () => {
    expect(readString({ headline: "hi" }, "headline")).toBe("hi");
    expect(readString({ headline: 42 }, "headline")).toBe("");
    expect(readString({}, "headline")).toBe("");
    expect(readString(null, "headline")).toBe("");
  });

  it("readYears returns the number's spelling and nothing else", () => {
    expect(readYears({ yearsExperience: 6 })).toBe("6");
    expect(readYears({ yearsExperience: 0 })).toBe("0");
    expect(readYears({ yearsExperience: "6" })).toBe("");
    expect(readYears({})).toBe("");
    expect(readYears(null)).toBe("");
  });
});
