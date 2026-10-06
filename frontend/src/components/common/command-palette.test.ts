import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";

/**
 * The palette can't render in the node environment, so these guard the wiring that
 * decides which rows reach the screen. The bug they exist for is a quiet one: /search
 * had already filtered, and a second title-only pass in here deleted the hits that
 * matched elsewhere in the row — so the palette printed "No results." over a server
 * answer that had rows.
 */
const source = readFileSync(
  new URL("./command-palette.tsx", import.meta.url),
  "utf8"
);

describe("the command palette's result list", () => {
  it("renders what the server returned, without re-matching titles", () => {
    expect(source).toContain("const apiGroups = results.data?.groups ?? [];");
    // The one regression this pins: a title substring test over the fetched items.
    expect(source).not.toMatch(/\.title\.toLowerCase\(\)\.includes/);
    // cmdk must stay out of the way too, or it filters again on its own. Anchor on the
    // JSX, not the word: a prose mention of the prop would satisfy a plain toContain.
    expect(source).toMatch(/<Command shouldFilter=\{false\}>/);
  });

  it("binds the request to the one parameter /search accepts", () => {
    // SearchController.search(@CurrentUser, @RequestParam String q) — anything else in the
    // query string is dropped by Spring, so a `size` here was an inert promise.
    expect(source).toMatch(/endpoints\.search,\s*\{ q \}\)/);
    expect(source).not.toMatch(/size:\s*8/);
  });

  it("states the searchable groups from the table that decodes them", () => {
    // The line used to hand-name four of the six groups the endpoint answers with, and then
    // said "once the API is live" — it is live now (SearchController answers GET /search),
    // so the sentence describes the streaming instead of promising a future.
    expect(source).toContain(
      "Search {searchGroupNames()} — content results stream in as you type."
    );
    expect(source).not.toContain("once the API is live");
    expect(source).not.toMatch(/resumes, jobs, companies and conversations/);
    expect(source).toContain('import { normalizeSearch, searchGroupNames } from "@/lib/api/normalize"');
  });

  it("keeps navigation filtering locally, since that list never leaves the client", () => {
    expect(source).toMatch(/NAV_ITEMS\.filter\(/);
  });
});
