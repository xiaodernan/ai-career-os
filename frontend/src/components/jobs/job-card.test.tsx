import { describe, expect, it, vi } from "vitest";
import * as React from "react";
import { readdirSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { renderToStaticMarkup } from "react-dom/server";

vi.mock("@/lib/i18n/locale-context", () => ({
  // The identity translator keeps the card's own text visible: a key the component asks for renders
  // as that key, so a copy change cannot hide a structural one.
  useLocale: () => ({ locale: "en", t: (key: string) => key, setLocale: () => {} }),
}));

import { JobCard } from "./job-card";
import type { Job } from "@/lib/api/types";

/**
 * The bare `0` on every recommended-job row, and the rule that keeps it from coming back.
 *
 * Measured on the running stack (2026-10-24, `demo+mvle37ja@careeros.test`): the dashboard's "Where to
 * focus" card lists five jobs, and each row's DOM is
 * `<div>…<div><h3>Imported job</h3><p>Unknown company</p></div>0</div>` -- a text node `0` between the
 * title block and the footer. The aggregate hands those rows as
 * `{title:"Imported job", companyName:"Unknown company", matchOverall:null, matchId:null}` with no
 * `skills` key at all, so `normalizeJob` gives `skills: []` and `latestMatch: null`.
 *
 * The card then evaluates `{(match?.matchedSkills?.length || match?.missingSkills?.length
 *  || job.skills?.length) && (<div>…</div>)}`. React renders `false`, `null` and `undefined` as nothing,
 * but it renders the NUMBER zero as the text "0" -- and an `||` chain of lengths ends on a number. So a
 * card with nothing to show shows a digit nobody put there, on the page that every signed-in user sees
 * first. The fix is to make the guard a boolean; the census below is why the fix is not just this line.
 */

const SRC = fileURLToPath(new URL("../../", import.meta.url));

const unscored: Job = {
  id: "job-1",
  companyId: "",
  title: "Imported job",
  companyName: "Unknown company",
  status: "open",
  skills: [],
  latestMatch: null,
};

/** What a visitor reads, with the markup stripped -- the digit is text, not an attribute. */
function visible(html: string): string {
  return html.replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim();
}

/* -- the census ------------------------------------------------------------- */

/** The guard the card used to carry, kept as shipped text so the scanner has a subject it can miss. */
const OLD_GUARD = `{(match?.matchedSkills?.length || match?.missingSkills?.length || job.skills?.length) && (
  <div className="mt-2.5">
    <SkillChips matched={match.matchedSkills} />
  </div>
)}`;

function* tsxFiles(dir: string): Generator<string> {
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const path = `${dir}/${entry.name}`;
    if (entry.isDirectory()) yield* tsxFiles(path);
    else if (entry.name.endsWith(".tsx")) yield path;
  }
}

/** How much of the tree this walk reads at landing; a smaller number means the walk, not the code, changed. */
const MIN_TSX = 120;

/** Walk back to the `{` that opens the container holding index `i`; -1 when there is none. */
function openBrace(text: string, i: number): number {
  let depth = 0;
  for (let j = i; j >= 0; j--) {
    const c = text[j];
    if (c === "}") depth += 1;
    else if (c === "{") {
      if (depth === 0) return j;
      depth -= 1;
    }
  }
  return -1;
}

/** Drop one layer of balanced outer parens, so `(a || b) && (…)` reads as `a || b`. */
function unwrap(guard: string): string {
  if (!guard.startsWith("(")) return guard;
  let depth = 0;
  for (let k = 0; k < guard.length; k += 1) {
    if (guard[k] === "(") depth += 1;
    else if (guard[k] === ")") {
      depth -= 1;
      if (depth === 0) return k === guard.length - 1 ? guard.slice(1, -1) : guard;
    }
  }
  return guard;
}

/**
 * Every `&& (` in `text` whose left-hand value can be a number.
 *
 * "Can be" is decided structurally: strip the container's parens, take the operand the `&&` actually
 * decides on (the tail after the last `||`/`&&`), and refuse it when it is already a boolean -- a
 * negation, a comparison, or a call. What is left is an operand ending in `.length`, which is exactly
 * how a card with no chips evaluates to `0`. A regex over `[^)]*` cannot read that guard because the
 * shipped one nests two optional chains and a call inside its own parentheses.
 */
function numericGuards(text: string): { line: number; tail: string }[] {
  const out: { line: number; tail: string }[] = [];
  for (const match of text.matchAll(/&&\s*[{(]/g)) {
    const brace = openBrace(text, match.index);
    if (brace < 0) continue;
    const guard = text.slice(brace + 1, match.index).replace(/\s+/g, " ").trim();
    if (!guard) continue;
    const tail = unwrap(guard).split(/\|\||&&/).pop()?.trim() ?? "";
    if (!/\.length\??$/.test(tail)) continue;
    // A tail that ends in `.length` is a number unless something already turned it into a boolean:
    // a negation (`!x.length`, `!!x.length`) or a comparison (`x.length > 0`). A call is not an
    // escape -- `items.filter(p).length` is exactly as numeric as `items.length`.
    if (/^!|[<>]=?|===?|!==?/.test(tail)) continue;
    out.push({ line: text.slice(0, match.index).split("\n").length, tail });
  }
  return out;
}

describe("the dense job card's evidence row", () => {
  it("renders no text where the skill chips would go when there is nothing to show", () => {
    const html = renderToStaticMarkup(<JobCard job={unscored} dense showSave={false} />);
    const read = visible(html);
    expect(read, `the card rendered "${read}": a job with no skills and no match has nothing to show, ` +
      `and React prints a numeric guard's 0 as the text "0"`).not.toMatch(/\b0\b/);
    // The render did happen -- without this, "no 0" is also true of an empty page.
    expect(read).toContain("Imported job");
    expect(read).toContain("Unknown company");
  });

  it("shows the job's own skills when the aggregate sent none (control)", () => {
    const html = renderToStaticMarkup(
      <JobCard job={{ ...unscored, skills: ["Kubernetes", "PostgreSQL"] }} dense showSave={false} />
    );
    const read = visible(html);
    expect(read).toContain("Kubernetes");
    expect(read).toContain("PostgreSQL");
    expect(read, `the chips came back with a digit attached: "${read}"`).not.toMatch(/\b0\b/);
  });

  it("shows the matched skills the agent named when a match is attached (control)", () => {
    const scored: Job = {
      ...unscored,
      skills: [],
      latestMatch: { id: "m-1", jobId: "job-1", overall: 0.66, matchedSkills: ["Kubernetes"] },
    };
    const read = visible(renderToStaticMarkup(<JobCard job={scored} dense showSave={false} />));
    expect(read).toContain("Kubernetes");
    // No "no digit" claim here: a scored row carries the MatchRing, whose first paint is the text
    // `0 %` because the arc animates up from zero. The digit this gate is about is the one that
    // appears where nothing was meant to render, which is what the two cases above hold.
  });
});

describe("JSX conditionals across the frontend", () => {
  it("reads the guard shape it is looking for, from a string no component ships", () => {
    // Without this, the census is green for as long as its scanner reads nothing.
    const found = numericGuards(OLD_GUARD);
    expect(found.length, "the scanner found no numeric guard inside its own fixture -- a chain of " +
      "lengths guarding a block is the shape it exists to read, and if it cannot see this one it " +
      "cannot see one in a component either").toBe(1);
    expect(found[0].tail).toBe("job.skills?.length");
  });

  it("finds no component that guards a block with a length", () => {
    const offenders: string[] = [];
    let walked = 0;
    for (const file of tsxFiles(SRC)) {
      if (file.endsWith(".test.tsx")) continue;
      walked += 1;
      const text = readFileSync(file, "utf8").replace(/\r\n/g, "\n");
      for (const guard of numericGuards(text)) {
        offenders.push(
          `${file.slice(SRC.length + 1)}:${guard.line} guards a block with \`${guard.tail}\` -- when ` +
            `every operand is empty the expression is the number 0 and React prints it as text`
        );
      }
    }
    expect(offenders, `${offenders.length} of ${walked} components would print a digit: ` +
      `${offenders.join("; ")}`).toEqual([]);
    // The floor comes from this same loop: a walk that stopped descending would report no offenders
    // because it read nothing, so the population it read has to be named in the same breath.
    expect(walked, `the census walked ${walked} .tsx files under frontend/src, below the ${MIN_TSX} ` +
      "that ship: a green from a walk that skipped a directory is a green about nothing")
      .toBeGreaterThanOrEqual(MIN_TSX);
  });

  it("refuses its own file, which is the one place the forbidden shape still appears", () => {
    // The `.test.tsx` skip is a hiding place unless the skipped population really would red.
    const here = readFileSync(fileURLToPath(import.meta.url), "utf8").replace(/\r\n/g, "\n");
    expect(numericGuards(here).length, "this file's own fixture no longer reads as a numeric guard, " +
      "so the skip below the walk excuses a population the scanner was never shown").toBeGreaterThan(0);
  });
});
