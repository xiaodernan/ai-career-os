import { describe, expect, it } from "vitest";

import {
  browserSources,
  everyOffender,
  textOffendersIn,
  TEXT_NODE_LIMIT,
} from "./copy-scan";

/**
 * The browser's copy census.
 *
 * Every page and panel in this product reads its wording from one table
 * (`lib/i18n/translations.ts`), and every piece of it can be read in the
 * reader's language. That was not true a while ago, and the fix was not
 * one edit: it was about two hundred strings across thirty files, and it
 * took the discipline of a gate to keep it.
 *
 * This is that gate. The scan itself lives in `copy-scan.ts`, and it finds
 * the copy-bearing attributes that still hold an English literal, the same
 * words inside object literals, the prose between the tags, the words in a
 * ternary or a `||` fallback, and a quoted sentence that is simply a value.
 * A string in any of those is a word the reader cannot change, and it is
 * the shape the fix took every time.
 *
 * The failure it catches is quiet in the worst way. A hardcoded string
 * compiles, renders, looks right in English and wrong in every other
 * language, and nothing goes red. The gate makes it red.
 *
 * The known list that used to live here is gone, and zero is the pin. The
 * list was a record of what was left; what is left is nothing. It stays
 * gone rather than becoming a budget: a new literal is a hole the gate
 * refuses, and the failure names the file and the string.
 */
describe("the browser's copy", () => {
  const found = everyOffender();

  it("reads its wording from the locale table, not from a literal", () => {
    // An empty answer is the whole gate now. The message names every
    // offender, so a regression reads as the file and the string.
    const offenders = found.map((o) => `${o.file} ${o.attribute}="${o.value}"`);
    expect(offenders, `copy is written into the browser's sources:\n${offenders.join("\n")}`).toEqual(
      [],
    );
  });

  it("has read the whole browser by now", () => {
    // The walk itself is the thing that can silently stop: a directory that
    // moves, a suffix that changes. A census of nothing is not a census.
    //
    // 131 files. The pin is a population, not a budget: a new file belongs
    // in it, and the count moves when one is added or removed. 129 with the
    // 404 body split out of `app/not-found.tsx` -- the page keeps its
    // `metadata` export and the localized body becomes a client component --
    // 130 with the language switch, which the two public surfaces need, and
    // 131 with `components/root-document.tsx`, the shell the layout renders so
    // `<html lang>` and the first paint carry the reader's language.
    expect(browserSources().length).toBe(131);
  });

  it("finds a sentence, however long it is", () => {
    // The scan's length bound was once short enough to hide most of the
    // product's prose: a sentence longer than about sixty characters sat
    // between the tags and the scan never read it. The long ones are the
    // ones that read as prose rather than as a label, so they are the
    // ones the gate is for.
    //
    // The known list used to hold the longest sentence the scan had to
    // read, and this test measured the bound against it. The list is empty
    // now, so the probe is synthetic: a sentence longer than any label,
    // between two tags, has to come back. A bound small enough to miss it
    // fails here, which is what keeps the gate's reach from shrinking
    // quietly.
    const sentence =
      "The pasted posting is judged by its trimmed length, so padding the field with spaces " +
      "cannot clear the floor, and the sentence that explains this is deliberately long enough " +
      "to be prose rather than a label.";
    expect(sentence.length).toBeGreaterThan(180);
    const probe = `export const x = <p>${sentence}</p>;`;
    expect(textOffendersIn("probe.tsx", probe)).toEqual([
      { file: "probe.tsx", attribute: "text", value: sentence },
    ]);
    expect(TEXT_NODE_LIMIT).toBeGreaterThan(sentence.length);
  });
});
