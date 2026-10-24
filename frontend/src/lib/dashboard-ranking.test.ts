import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { normalizeJob } from "@/lib/api/normalize";
import { translations } from "@/lib/i18n/translations";
import type { Job } from "@/lib/api/types";
import { RANKING_HINT_KEYS, rankingHintKey } from "./dashboard-ranking";

/**
 * The dashboard band that says how its list was ordered, and what it is allowed to claim.
 *
 * Measured on the running stack (2026-10-24, `demo+mvle37ja@careeros.test`): "Where to focus"
 * printed "Ranked by the matching agent against your resume." over five rows, every one of them
 * sent by `/reports/dashboard` as
 * `{title:"Imported job", companyName:"Unknown company", matchOverall:null, matchId:null}`.
 * No agent had ranked anything.
 *
 * `DashboardRepository.recommendedJobs` LEFT JOINs the viewer's latest match and ends with
 * `ORDER BY m.overall DESC NULLS LAST, j.posted_at DESC`. With no match row for anyone that
 * first key collapses to nothing and the list is pure recency — so the page was printing a
 * ranking sentence for a list the agent never touched. It decided the sentence by
 * `recommendedJobs?.length`, which asks "are there rows?" and answers "did the agent rank them?".
 *
 * These cases hold the three things that are now true instead: the score decides the sentence,
 * the score is read the way the shipped mapper projects it (so a wire spelling the mapper stops
 * reading cannot silently become "unranked" or "ranked"), and the page asks the helper rather
 * than doing its own arithmetic. The last one needs a structural witness, because the page is
 * where the bug lived and no behavior test can reach it.
 */

const PAGE = fileURLToPath(new URL("../app/(app)/dashboard/page.tsx", import.meta.url));
const RANKED = "dashboard.skillGapsHint";
const UNRANKED = "dashboard.straightFromTheBoard";

/** One aggregate row, projected by the mapper the app actually runs — not by a hand-written Job. */
function row(raw: Record<string, unknown> = {}): Job {
  return normalizeJob({
    id: "job-1",
    title: "Imported job",
    companyName: "Unknown company",
    matchOverall: null,
    matchId: null,
    ...raw,
  });
}

describe("the sentence the 'Where to focus' band is allowed to print", () => {
  it("offers the board when the aggregate sent rows but ranked none of them", () => {
    const rows = [row(), row({ id: "job-2" }), row({ id: "job-3" })];
    expect(rows.every((r) => r.latestMatch == null), "the fixture stopped being unscored").toBe(true);
    expect(
      rankingHintKey(rows),
      "every matchOverall was null, so the ORDER BY fell through to posted_at: this list has no ranking in it"
    ).toBe(UNRANKED);
  });

  it("names the agent when a row carries its score (flat wire spelling)", () => {
    expect(
      rankingHintKey([row(), row({ id: "job-2", matchOverall: 0.72, matchId: "m-2" })]),
      "a scored row is the agent's answer; the list is not the board's own order"
    ).toBe(RANKED);
  });

  it("names the agent when the score arrives nested (detail spelling)", () => {
    expect(
      rankingHintKey([row(), row({ id: "job-2", latestMatch: { id: "m-2", jobId: "job-2", overall: 0.6 } })]),
      "the nested spelling is the other way the mapper delivers a score"
    ).toBe(RANKED);
  });

  it("names the agent for snake_case, which is the other spelling the mapper tolerates", () => {
    expect(
      rankingHintKey([row({ match_overall: 0.4, match_id: "m-1" })]),
      "the mapper reads snake_case too, so a score in it is still a ranking"
    ).toBe(RANKED);
  });

  it("counts a score of zero as an answer the agent gave", () => {
    const scored = row({ matchOverall: 0, matchId: "m-1" });
    expect(scored.latestMatch, "the mapper drops a 0 and the band would then blame the mapper").not.toBeNull();
    expect(scored.latestMatch!.overall).toBe(0);
    expect(
      rankingHintKey([scored]),
      "0 is a ranking result, not an absence of one -- truthiness here would print the board's sentence over a scored row"
    ).toBe(RANKED);
  });

  it("names the agent when only the head of the list was scored", () => {
    // NULLS LAST puts the scored rows first, so the order at the head IS the agent's doing.
    // `every` would refuse the sentence here and be wrong about how the query ordered the list.
    const rows = [row({ matchOverall: 0.9, matchId: "m-1" }), row({ id: "job-2" }), row({ id: "job-3" })];
    expect(
      rankingHintKey(rows),
      "NULLS LAST ordered the scored rows first, so the head of this list is the agent's doing"
    ).toBe(RANKED);
  });

  it("offers the board when the aggregate omitted the section or has not answered yet", () => {
    expect(
      rankingHintKey(undefined),
      "no aggregate answer means no rows at all: this band is about rows, so it cannot claim a ranking"
    ).toBe(UNRANKED);
    expect(
      rankingHintKey([]),
      "an empty list is not a ranked one -- every([]) is vacuously true and would promise a ranking over nothing"
    ).toBe(UNRANKED);
  });

  it("only ever returns a key the locale table carries, in both languages", () => {
    // `used-keys.test.ts` reads `t("literal")` calls. This band now asks for its key through a
    // variable, so that gate cannot see it -- and a key the table does not hold renders as the
    // raw key on the reader's screen, in every language. This is the only reader of that claim.
    const en = new Set(leaves(translations.en));
    const zh = new Set(leaves(translations.zh));
    expect(RANKING_HINT_KEYS.length, "the helper's own key list is empty, so this case grades nothing")
      .toBeGreaterThanOrEqual(2);
    for (const key of RANKING_HINT_KEYS) {
      expect(en, `${key} is a key no English table entry answers`).toContain(key);
      expect(zh, `${key} has no Chinese entry, so a Chinese reader sees the key itself`).toContain(key);
    }
  });

});

describe("the page that prints it", () => {
  const pageText = () => readFileSync(PAGE, "utf-8").replace(/\r\n/g, "\n");

  it("asks the helper, and reads the aggregate's rows rather than their count", () => {
    const expr = bandDescription(pageText(), "dashboard.whereToFocus");
    expect(expr, "the band's description prop is no longer where this page chooses its sentence").not.toBeNull();
    expect(
      expr,
      `the band no longer asks the helper -- it decides from the rows themselves, by a length or by ` +
        `one hardcoded sentence: description={${expr}}`
    ).toContain("rankingHintKey(");
    expect(expr, `the band no longer hands the helper the aggregate's rows: description={${expr}}`)
      .toContain("data?.recommendedJobs");
    expect(
      expr,
      `a length is what told this band to promise a ranking it had no evidence for: description={${expr}}`
    ).not.toMatch(/\.length\b/);
  });

  it("reads the shape it is refusing, from a string the page used to ship", () => {
    // Without this, the witness above is green for as long as its reader cannot see the shape --
    // and the shape it was written for is exactly the multi-line ternary below.
    const found = bandDescription(OLD_BAND, "dashboard.whereToFocus");
    expect(found, "the reader cannot see a multi-line ternary, so it cannot see one in a page either").not.toBeNull();
    expect(found).not.toContain("rankingHintKey(");
    expect(found).toMatch(/\.length\b/);
  });

  it("refuses a band whose description is not in the same element as its title", () => {
    // The reader stops at the next band's title. A `description=` below that line belongs to a
    // different card, and reading it as this band's would be a green about the wrong sentence.
    expect(bandDescription(
      'title={t("dashboard.whereToFocus")} <Card /> title={t("dashboard.attention")} description={count}',
      "dashboard.whereToFocus"
    )).toBeNull();
    expect(bandDescription('title={t("nope")} description={count}', "dashboard.whereToFocus")).toBeNull();
  });
});

/** The band whose title reads `titleNeedle`, and the `description={...}` expression beside it. */
function bandDescription(text: string, titleNeedle: string): string | null {
  const title = text.indexOf(`title={t("${titleNeedle}")}`);
  if (title < 0) return null;
  const next = text.indexOf("title={t(", title + 1);
  const limit = next < 0 ? text.length : next;
  const at = text.indexOf("description={", title);
  if (at < 0 || at >= limit) return null;
  return braces(text, at + "description=".length);
}

/** The inside of the balanced `{...}` starting at `i`, whitespace collapsed; null when it never closes. */
function braces(text: string, i: number): string | null {
  if (text[i] !== "{") return null;
  let depth = 0;
  for (let j = i; j < text.length; j += 1) {
    if (text[j] === "{") depth += 1;
    else if (text[j] === "}") {
      depth -= 1;
      if (depth === 0) return text.slice(i + 1, j).replace(/\s+/g, " ").trim();
    }
  }
  return null;
}

/** The band's pre-fix text, kept so the reader above has a subject it can prove it can see. */
const OLD_BAND = `title={t("dashboard.whereToFocus")}
                    description={
                      data?.recommendedJobs?.length
                        ? t("dashboard.skillGapsHint")
                        : t("dashboard.straightFromTheBoard")
                    }`;

/** Every leaf key of a locale table, dotted -- the shape `t()` is called with. */
function leaves(value: unknown, prefix = ""): string[] {
  if (typeof value !== "object" || value === null) return [prefix];
  return Object.entries(value as Record<string, unknown>).flatMap(([k, v]) =>
    leaves(v, prefix ? `${prefix}.${k}` : k)
  );
}
