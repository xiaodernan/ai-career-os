import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative } from "node:path";
import { fileURLToPath } from "node:url";

/**
 * The browser's copy, and how to find it.
 *
 * The scan used to live inside the census's test file, and the script that
 * regenerates the census's list had a second copy of it. Two copies of one
 * rule is two rules: the moment they drifted, the list was regenerated from
 * a different population than the gate measured, and the gate stopped
 * meaning anything. So the scan lives here, and both read it.
 *
 * The scan finds three shapes of hardcoded copy in the browser's own
 * sources:
 *
 *   1. A copy-bearing *attribute*: `<Button title="Delete" />`.
 *   2. The *text between the tags*: `>Back to jobs<`.
 *   3. A copy-bearing *property in an object literal*: `{ label: "Technical" }`.
 *
 * The third was the blind spot, and it was the widest one. Half the
 * product's copy is written as an object literal -- a `DimensionBars` row, an
 * `EmptyState`, a list of stage names, the kinds a document may have -- and
 * the census read the first two shapes only. A bar labelled "Technical" on
 * a Chinese page was exactly as invisible to the gate as an attribute was:
 * it compiled, it rendered, it looked right in English, and nothing went
 * red.
 */

const ROOT = fileURLToPath(new URL("../../", import.meta.url));

/**
 * The attributes and properties that carry a word the reader sees or hears.
 *
 * A `label` is a word whether it was written `label="..."` or `label: "..."`,
 * so both shapes read the same list. `eyebrow` and `heading` are here
 * because this product's own components use them that way -- a section's
 * small overline and a command group's title -- and a word there is a word
 * the reader cannot change.
 */
export const COPY_ATTRIBUTES = [
  "title",
  "description",
  "label",
  "placeholder",
  "aria-label",
  "confirmLabel",
  "ctaLabel",
  "alt",
  "eyebrow",
  "heading",
];

/**
 * The words that are not copy.
 *
 * The brand is written as two tags -- `Career<span>OS</span>` -- so the
 * scanner sees a text node that begins with a capital. It is a name, not a
 * sentence, and it is the same name in every language, so it is excluded
 * rather than listed as a hole to close.
 *
 * A key name is the same kind of thing: "Ctrl K" is the name the platform
 * gives a key, and it is that on a Chinese machine too. It is not a word
 * the product writes, and translating it would name a key that does not
 * exist.
 */
export const NOT_COPY = new Set(["Career", "CareerOS", "OS", "AI Career OS", "Ctrl K", "⌘K"]);

/** One hardcoded copy string: the file it is in, and the string itself. */
export interface Offender {
  file: string;
  attribute: string;
  value: string;
}

/**
 * Every `.tsx` under the browser's own *screen* tree, tests aside.
 *
 * The population is narrower than it looks, and the narrowness is worth
 * knowing: this reads `app/` and `components/`, and only `.tsx`. So a
 * `.ts` module is invisible to it, and so is the whole of `lib/`.
 *
 * That is not a small hole. Measured on 2026-10-21 by pointing this scan at
 * the files it does not read: `.ts` files alone hold 41 more strings (the
 * navigation table's own labels and descriptions, the hooks' failure
 * messages, the auth-recovery form's validation text), and `lib/` holds
 * about a thousand. Most of the `lib/` ones are vocabularies -- a table of
 * English fallbacks beside the keys that translate them -- which is exactly
 * why they live in a module the census does not reach: a fallback table is a
 * vocabulary, not a hole to close.
 *
 * But not all of them are. The navigation table had two items with no
 * translation key at all, so they rendered their English names on every
 * language, and nothing here could see it. So the scan's population is
 * stated here rather than left implicit: **a gate measures the population
 * it can see, and a hole in the scan is a hole in the product.**
 */
export function browserSources(): string[] {
  const out: string[] = [];
  const walk = (dir: string) => {
    for (const entry of readdirSync(dir)) {
      const full = join(dir, entry);
      if (statSync(full).isDirectory()) {
        walk(full);
        continue;
      }
      if (!entry.endsWith(".tsx")) continue;
      if (entry.includes(".test.")) continue;
      out.push(relative(ROOT, full).replace(/\\/g, "/"));
    }
  };
  walk(join(ROOT, "app"));
  walk(join(ROOT, "components"));
  return out.sort();
}

/**
 * The text between two tags: `>Back to jobs<`.
 *
 * This is where most of the product's prose lives -- the sentences between
 * a heading and a list, the button that says "Try again". The attribute
 * scan catches the labels; this catches the sentences.
 *
 * Two shapes count. A text node is `>prose<`, and a text node with an
 * expression in it is `>prose{count}<` -- the phrase is still a phrase,
 * and "Clear {count}" is a whole key. So the scan anchors on a tag or a
 * closing brace and reads up to the next tag or opening brace.
 *
 * The value may start with whitespace -- a `>` is usually the end of an
 * opening tag, and the prose begins on the next line -- so the value is
 * trimmed before it is read.
 *
 * The anchor is a `>` that is not an arrow's. `type SearchFn = (q: string) =>
 * Promise<SearchResults>` has a `>` in it, and the type after it read as a
 * text node -- a word the reader never sees, named in the gate's list of
 * things to fix, and not fixable by any edit to the source that made it
 * true.
 *
 * The filter is the interesting part. A `>` in JSX is also a comparison
 * operator, so `total > PAGE_SIZE` reads as a text node that begins with
 * "PAGE_SIZE". A candidate carrying a character that cannot appear in a
 * sentence the reader reads is code, not copy, and is skipped.
 *
 * The length bound is generous, and it was not always. At eighty
 * characters the scan missed every sentence longer than about sixty --
 * which is most of them, and the long ones are the ones that read as
 * prose rather than as a label. The bound was never what kept the scan
 * honest: the lazy quantifier stops at the first `<` or `{` anyway, and
 * a text node cannot span a nested element because the character class
 * excludes the angle brackets and the braces. So the bound is only a
 * backstop against a run of text with no markup in it at all, and a
 * backstop that hides the copy is worse than no backstop.
 *
 * What this does not catch is the lowercase fragments: `} matching{" "}` is
 * the tail of a sentence whose other pieces are elsewhere, and a lone
 * word like that is not a phrase a translation key can hold. Those are a
 * known limit of the scan, not an oversight.
 */
/**
 * The longest text node the scan will read.
 *
 * It was once eighty, which was short enough to hide most of the
 * product's prose: a sentence longer than about sixty characters sat
 * between the tags and the scan never read it. The long ones are the ones
 * that read as prose rather than as a label, so they are the ones the
 * gate is for.
 *
 * The bound was never what kept the scan honest: the lazy quantifier
 * stops at the first `<` or `{` anyway, and a text node cannot span a
 * nested element because the character class excludes the angle brackets
 * and the braces. So the bound is only a backstop against a run of text
 * with no markup in it at all, and a backstop that hides the copy is
 * worse than no backstop.
 */
export const TEXT_NODE_LIMIT = 400;

const TEXT_NODE = new RegExp(
  `(?:(?<!=)>|\\})([^<>{}]{1,${TEXT_NODE_LIMIT}}?)(?=<|\\{)`,
  "g"
);

/** A copy-bearing attribute: `title="Delete"`. */
const ATTRIBUTE = new RegExp(`\\b(${COPY_ATTRIBUTES.join("|")})="([^"\\n]+)"`, "g");

/** A copy-bearing property in an object literal: `label: "Technical"`. */
const OBJECT_LITERAL = new RegExp(`\\b(${COPY_ATTRIBUTES.join("|")}):\\s*"([^"\\n]+)"`, "g");

/**
 * The code characters that mean a candidate is code and not copy.
 *
 * A bracket, a brace, a semicolon, an equals, a pipe, an angle bracket, an
 * ampersand, an underscore. A *parenthesis* is not on the list:
 * "(single-call parses)" is ordinary punctuation in an English sentence, and
 * rejecting a candidate for carrying one hid a sentence the reader would
 * have seen.
 */
const CODE_CHARS = /[{};=<>|&_]/;

/** A candidate is code if it carries one of the code characters. */
function isCode(value: string): boolean {
  return CODE_CHARS.test(value.replace(/&[a-z]+;/g, "x"));
}

function attributeOffenders(): Offender[] {
  const found: Offender[] = [];
  for (const rel of browserSources()) {
    const text = readFileSync(join(ROOT, rel), "utf-8");
    for (const m of text.matchAll(ATTRIBUTE)) {
      const value = m[2];
      // A word that starts lower-case is an identifier, a URL fragment or a
      // token, not a sentence. A single word that starts upper-case is a
      // label ("Delete", "Save") and does count.
      if (!/^[A-Z]/.test(value)) continue;
      // A class name, a path or a slug never starts with a capital and a
      // space; a copy string nearly always does.
      found.push({ file: rel, attribute: m[1], value });
    }
  }
  return found;
}

function objectLiteralOffenders(): Offender[] {
  const found: Offender[] = [];
  for (const rel of browserSources()) {
    const text = readFileSync(join(ROOT, rel), "utf-8");
    for (const m of text.matchAll(OBJECT_LITERAL)) {
      const value = m[2];
      // The same rule as the attribute scan.
      if (!/^[A-Z]/.test(value)) continue;
      found.push({ file: rel, attribute: m[1], value });
    }
  }
  return found;
}

/**
 * The text nodes of one source. Exported so the gate can feed the scan a
 * sentence longer than anything in the tree and see it come back: once the
 * known list is empty there is no real long string left to measure the
 * bound against, and a bound nothing tests is a bound that can shrink.
 */
export function textOffendersIn(file: string, text: string): Offender[] {
  const found: Offender[] = [];
  for (const m of text.matchAll(TEXT_NODE)) {
    const value = m[1].trim();
    if (!value) continue;
    // A translation key that was never resolved. The reader sees the key
    // instead of the copy, and it is the one failure the prose rules below
    // would miss -- so it is caught here rather than by them.
    const unresolved = /^[a-z][a-zA-Z]*(\.[a-z][a-zA-Z]*)+$/.test(value);
    if (!unresolved) {
      // A sentence starts with a capital and a lower-case letter after it.
      // "AI", "OS" and "JD" are names, not sentences.
      if (!/^[A-Z][a-z]/.test(value)) continue;
    }
    // Code, not copy.
    if (isCode(value)) continue;
    if (NOT_COPY.has(value)) continue;
    found.push({ file, attribute: "text", value });
  }
  return found;
}

function textNodeOffenders(): Offender[] {
  return browserSources().flatMap((rel) =>
    textOffendersIn(rel, readFileSync(join(ROOT, rel), "utf-8"))
  );
}

/**
 * The copy in a JSX expression.
 *
 * `{cond ? "Interview-ready" : "Needs work"}` is a word the reader sees,
 * and the text-node scan never reads it: an expression is not text. This
 * was the last shape the copy was written in that the gate could not see,
 * and it held a good deal of the product's prose -- the words a card
 * shows when one thing is true and another when it is not.
 *
 * The scan looks for a literal in a ternary or a logical fallback, which
 * is where the copy in an expression lives. A ternary is read as a whole
 * -- both of its branches -- because the second branch is exactly as
 * much copy as the first, and reading only the first would leave half of
 * them out.
 *
 * The filter is the one the other scans use: a word that starts
 * lower-case is an identifier, and one that is entirely upper case is a
 * code -- a variant name, a language tag, an initialism.
 */
const TERNARY = /\?\s*"([^"\\]{2,})"\s*:\s*"([^"\\]{2,})"/g;
const FALLBACK = /\|\|\s*"([^"\\]{2,})"/g;

function expressionOffenders(): Offender[] {
  const found: Offender[] = [];
  for (const rel of browserSources()) {
    const text = readFileSync(join(ROOT, rel), "utf-8");
    const seen = new Set<string>();
    for (const m of text.matchAll(TERNARY)) {
      seen.add(m[1]);
      seen.add(m[2]);
    }
    for (const m of text.matchAll(FALLBACK)) {
      seen.add(m[1]);
    }
    for (const value of seen) {
      // A sentence starts with a capital and a lower-case letter after it.
      if (!/^[A-Z][a-z]/.test(value)) continue;
      // Entirely upper case is a code: a variant, a language tag, an
      // initialism. "EN" is a language, not a word.
      if (/^[A-Z\s]+$/.test(value)) continue;
      // Code characters.
      if (isCode(value)) continue;
      if (NOT_COPY.has(value.trim())) continue;
      found.push({ file: rel, attribute: "expression", value });
    }
  }
  return found;
}

/**
 * The source with its comments removed.
 *
 * A comment is a note to the next reader, not a word the reader sees, and
 * the scan reads strings -- so a sentence quoted inside a comment is
 * copy-shaped but it is nobody's copy. The comments in this repository are
 * full of them: "No data" is an em dash, not a zero", "the row mapper only
 * falls back to 'Untitled note' when the title is absent".
 *
 * The stripper tracks the strings, so a `//` inside one is not mistaken for
 * a comment, and a `/*` inside one is not mistaken for a block.
 */
/**
 * The source with its comments removed.
 *
 * Exported because the other gate that reads the browser's sources needs the
 * same rule: a `t("...")` in a comment is not a key the browser asks for, and
 * a gate that counted it would ask for a key that does not exist.
 */
export function stripComments(source: string): string {
  let out = "";
  let i = 0;
  let quote: string | null = null;
  while (i < source.length) {
    const ch = source[i];
    const next = source[i + 1];
    if (quote) {
      out += ch;
      if (ch === "\\") {
        out += next ?? "";
        i += 2;
        continue;
      }
      if (ch === quote) quote = null;
      i++;
      continue;
    }
    if (ch === '"' || ch === "'" || ch === "`") {
      quote = ch;
      out += ch;
      i++;
      continue;
    }
    if (ch === "/" && next === "*") {
      const end = source.indexOf("*/", i + 2);
      i = end < 0 ? source.length : end + 2;
      out += " ";
      continue;
    }
    if (ch === "/" && next === "/") {
      const end = source.indexOf("\n", i);
      i = end < 0 ? source.length : end;
      out += " ";
      continue;
    }
    out += ch;
    i++;
  }
  return out;
}

/**
 * The copy in a string literal.
 *
 * The last shape. A toast message, an empty state's sentence, a
 * placeholder, an `aria-label` -- all of them are quoted literals, and
 * all of them are words the reader sees in a language they did not
 * choose.
 *
 * The rule is the two things a sentence has and an identifier does not: it
 * starts with a capital, and it has a space in it. A class name, a route,
 * a colour, a key -- none of them are a capitalised phrase. The single
 * word is left to the other scans, which read the positions a phrase is
 * usually written in.
 *
 * The last character matters too. A phrase ends in a letter or in
 * punctuation that closes a sentence -- a full stop, a question mark, an
 * exclamation, a closing bracket -- and a candidate that ends in a comma
 * or an open bracket is a fragment of an expression that the quote
 * matching paired wrongly. The scanner reads quotes, and a JSX expression
 * that contains one puts the pairs out of step: `{MAX_DOCUMENT_BYTES /
 * (1024 * 1024)} MB each, {ACCEPTED_EXTENSIONS.join(" / ")}` pairs the
 * quotes around `" / "` and reads the code on either side of it.
 */
const LITERAL = /"([^"\\\n]{2,})"/g;
const SENTENCE_END = /[a-zA-Z.!?)\]…]$/;

function literalOffenders(): Offender[] {
  const found: Offender[] = [];
  for (const rel of browserSources()) {
    const text = stripComments(readFileSync(join(ROOT, rel), "utf-8"));
    const seen = new Set<string>();
    for (const m of text.matchAll(LITERAL)) {
      const value = m[1];
      // A capital, and a space: a phrase rather than an identifier.
      if (!/^[A-Z][a-z]/.test(value)) continue;
      if (!value.includes(" ")) continue;
      if (!SENTENCE_END.test(value)) continue;
      if (isCode(value)) continue;
      if (NOT_COPY.has(value.trim())) continue;
      seen.add(value);
    }
    for (const value of seen) {
      found.push({ file: rel, attribute: "literal", value });
    }
  }
  return found;
}

/**
 * Every hardcoded string: the attributes, the object literals, the text,
 * the expressions and the literals.
 *
 * The count is of *distinct* strings: the same sentence can be read by
 * more than one scan -- a `title="Delete"` is an attribute and a literal
 * -- and a population that counted it twice would not be a population.
 */
export function everyOffender(): Offender[] {
  const all = [
    ...attributeOffenders(),
    ...objectLiteralOffenders(),
    ...textNodeOffenders(),
    ...expressionOffenders(),
    ...literalOffenders(),
  ];
  const seen = new Set<string>();
  const out: Offender[] = [];
  for (const o of all) {
    const key = `${o.file} ${o.value}`;
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(o);
  }
  return out;
}
