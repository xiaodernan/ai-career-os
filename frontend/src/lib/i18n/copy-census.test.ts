import { describe, expect, it } from "vitest";

import {
  browserSources,
  everyOffender,
  templateOffendersIn,
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
    // `<html lang>` and the first paint carry the reader's language, and 132
    // with the saved-search panel beside the board's filters, and 133 with
    // `components/ingestion/scheduled-feeds-panel.tsx`, the browser's half of
    // the nightly sweep (19.2), and 134 with `app/(app)/notifications/page.tsx`,
    // the inbox the synthesized signals land in (19.3), and 135 with
    // `components/monitoring/nightly-history.tsx`, the card the nightly job's
    // own results are read from (20.1), and 136 with
    // `components/settings/push-card.tsx`, the switch that rings this browser
    // (33.4), and 137 with `components/settings/calendar-card.tsx`, the address
    // the reader pastes into a calendar app (34.1), and 138 with
    // `components/settings/security-card.tsx`, the second door's status and codes
    // (36.4), and 140 with the replies surface (37.4): `app/(app)/replies/page.tsx`
    // lists the letters and `components/settings/inbound-card.tsx` hands out the
    // address they are forwarded to. (`lib/hooks/replies.ts` is the `.ts` half and
    // was never part of this walk.)
    expect(browserSources().length).toBe(140);
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

  it("reads the tail of a sentence split around a value", () => {
    // `{replied} of {applied} submitted applications got a reply.` reads as
    // one sentence and is cut into three text nodes, and the last one
    // begins lower-case. The capital rule skipped it, so the rates card
    // said this in English on a Chinese page and no gate looked at it.
    const probe = "export const x = <p>{replied} of {applied} submitted applications got a reply.</p>;";
    expect(textOffendersIn("probe.tsx", probe).map((o) => o.value)).toEqual([
      "submitted applications got a reply.",
    ]);
  });

  it("still leaves a lone lower-case word alone", () => {
    // The tail rule needs a phrase: a space and a closing mark. A single
    // word after a value is the piece of a sentence whose other pieces are
    // elsewhere, and no key can hold it.
    const probe = "export const x = <p>{count} matching {noun}</p>;";
    expect(textOffendersIn("probe.tsx", probe)).toEqual([]);
    // The head rule needs a phrase for the same reason: `ms` is a unit the
    // reader reads in either language, not a word a key can hold.
    const unit = "export const x = <p>ms</p>;";
    expect(textOffendersIn("probe.tsx", unit)).toEqual([]);
  });

  it("reads the head of a sentence split around a value", () => {
    // The depth badge read `reached depth 3 / 5 · Solid` on a Chinese page:
    // the first chunk begins lower-case and carries no closing mark, so the
    // capital rule and the tail rule both skipped it. A chunk that opens a
    // tag as a multi-word lower-case phrase is that head.
    const probe = "export const x = <p>reached depth {level} / 5 · {band}</p>;";
    expect(textOffendersIn("probe.tsx", probe).map((o) => o.value)).toEqual(["reached depth"]);
    const whole = "export const x = <span>hover the dots for each question</span>;";
    expect(textOffendersIn("probe.tsx", whole).map((o) => o.value)).toEqual([
      "hover the dots for each question",
    ]);
  });

  it("does not read code the text-node regex caught out of alignment", () => {
    // A regex that reads between `>` and `{` also reads code that happens to
    // sit in those characters. A statement's opening word, or the punctuation
    // of an expression, is not a sentence the reader sees.
    const probes = [
      "export const x = () => {\n  if (!ready) return;\n};",
      "const y = a > b ? c : d;",
      "const z = list.map((v) => v.name).join(\", \");",
    ];
    for (const probe of probes) expect(textOffendersIn("probe.tsx", probe)).toEqual([]);
  });

  it("reads the prose a template literal carries between its values", () => {
    // The five scanners above all read a double-quoted string; a backtick
    // was not a quote to any of them. Fourteen templates across twelve
    // screens carried a label or a sentence -- an `aria-label` around a
    // row's title, a version row's fallback name -- and no gate read one.
    //
    // The second probe puts an object literal and an arrow inside the
    // interpolation: the reader has to count braces to find the `}` that
    // ends the expression, or the rest of the template is read as one chunk.
    const probe = [
      'export const a = <span aria-label={`Version ${v.versionNo ?? v.id.slice(0, 8)}`} />;',
      'export const b = <span title={`Group ${rows.map((r) => ({ id: r.id })).length}`} />;',
    ].join("\n");
    expect(templateOffendersIn("probe.tsx", probe).map((o) => o.value)).toEqual([
      "Version",
      "Group",
    ]);
  });

  it("leaves a template that is a value or a class name alone", () => {
    const probe = [
      "export const a = <span className={`px-${n} py-2`} />;",
      "export const b = <a href={`/jobs/${id}`} />;",
      "export const c = <span>{`${done}/${total}`}</span>;",
    ].join("\n");
    expect(templateOffendersIn("probe.tsx", probe)).toEqual([]);
  });

  it("reads the chunk a value left behind, mark and all", () => {
    // `“${file.name}” is over the cap.` cuts the literal at `” is over the
    // cap.` -- the first character is the mark that closed around the value,
    // so the sentence's first *word* is behind a space and a quotation mark.
    // A head rule that reads only the first character skips it.
    const probe = "export const x = `“${file.name}” is over the 20 MB ingestion cap.`;";
    expect(templateOffendersIn("probe.tsx", probe).map((o) => o.value)).toEqual([
      "is over the 20 MB ingestion cap.",
    ]);
  });
});
