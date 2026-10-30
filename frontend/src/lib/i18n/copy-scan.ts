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
 * The lower-case *sentence* is the shape the capital rule used to hide. A
 * sentence split around a value -- `{replied} of {applied} submitted
 * applications got a reply.` -- is cut into fragments, and the fragment
 * after a value begins lower-case because the value is the sentence's
 * subject. The capital rule skipped it, so an entire English sentence could
 * sit between two expressions and the census never read it; three did.
 * A fragment with a space and a closing mark is the tail of a sentence, and
 * the tail of a sentence is copy: it is read now.
 *
 * What the rule still does not catch is the lone lower-case word:
 * `} matching{" "}` is a piece of a sentence whose other pieces are
 * elsewhere, and no translation key can hold it by itself. A fragment with
 * a space but no closing mark is read by {@link sentenceContinuation}.
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
    if (
      !unresolved &&
      !sentenceHead(value) &&
      !sentenceTail(value) &&
      !sentenceLead(value, m[0][0]) &&
      !sentenceContinuation(value, m[0][0])
    )
      continue;
    // Code, not copy.
    if (isCode(value)) continue;
    if (NOT_COPY.has(value)) continue;
    found.push({ file, attribute: "text", value });
  }
  return found;
}

/**
 * The value with the punctuation a sentence may open with stripped.
 *
 * A template chunk does not have to start at the sentence's first word: the
 * chunk after a value is the sentence's tail, and it may open with the
 * quotation mark that closed around the value -- `“${file.name}” is over the
 * cap.` cuts the chunk at `” is over the cap.`, whose first character is
 * punctuation and whose first *word* is lower-case. Reading the head without
 * stripping the mark hid the sentence, so both rules read the bare form.
 */
function bare(value: string): string {
  return value.replace(/^[\s"“”'(\[]+/, "");
}

/**
 * The start of a sentence: a capital and a lower-case letter after it.
 * "AI", "OS" and "JD" are names, not sentences.
 */
function sentenceHead(value: string): boolean {
  return /^[A-Z][a-z]/.test(bare(value));
}

/**
 * The tail of a sentence that was split around a value.
 *
 * `{replied} of {applied} submitted applications got a reply.` reads as one
 * sentence to the reader and as three text nodes to the scan; the last one
 * begins lower-case. A fragment that has a space in it and ends in a
 * closing mark is that tail -- a whole phrase a key can hold -- rather
 * than the identifier the capital rule was written to skip.
 */
function sentenceTail(value: string): boolean {
  const head = bare(value);
  return /^[a-z]/.test(head) && /\s/.test(head) && /[.!?…]$/.test(head);
}

/** A JS statement's opening word: a chunk that starts with one is code the
 *  text-node regex caught out of alignment, not a sentence the reader sees. */
const CODE_HEAD =
  /^(export|import|return|if|else|case|catch|function|const|let|var|await|from|type|interface|declare|throw|new|typeof|default)\b/;

/**
 * The head of a sentence that was split around a value.
 *
 * `reached depth {level} / 5 · {band}` reads as one sentence and is cut into
 * a text node and an expression; the first node begins lower-case and carries
 * no closing mark, so the capital rule and the tail rule both skipped it and
 * the report printed that line in English on a Chinese page. A chunk that
 * opens right after a tag and is a multi-word lower-case phrase is that head.
 * Code is excluded by shape: a statement keyword at the start, or a quote or
 * parenthesis a sentence does not sit inside of.
 */
function sentenceLead(value: string, opened: string): boolean {
  if (opened !== ">") return false;
  const head = bare(value);
  return /^[a-z]/.test(head) && /\s/.test(head) && !/["()]/.test(head) && !CODE_HEAD.test(head);
}

/**
 * The continuation a value left behind.
 *
 * `{count} runs analyzed`, `{covered} covered · {partial} partial`, `{n}
 * matched postings` -- a lower-case phrase that follows a value and carries
 * no closing mark. The head rule needs a tag anchor and the tail rule needs
 * a full stop, so both skipped it: seven such fragments printed English
 * count sentences inside Chinese cards with the gate green.
 *
 * The shape is the template scan's fragment rule ({@link sentenceFragment}):
 * the separators `·—–,` are spacing, everything else has to be a lower-case
 * word, and one word of at least three letters is what makes it a phrase
 * rather than a unit like `ms`. A statement keyword is code the
 * brace-anchored regex caught out of alignment, not a sentence.
 */
function sentenceContinuation(value: string, opened: string): boolean {
  if (opened !== "}") return false;
  const head = bare(value);
  if (!/^[a-z]/.test(head)) return false;
  if (!/\s/.test(head)) return false;
  if (CODE_HEAD.test(head)) return false;
  const words = head.replace(/[·—–,]/g, " ").replace(/\s+/g, " ").trim();
  if (!/^[a-z]+( [a-z]+)*$/.test(words)) return false;
  return words.split(" ").some((word) => word.length >= 3);
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
 * The copy in a template literal.
 *
 * The last shape, and the one every other scan was blind to. The five
 * scanners above all read a double-quoted string; a backtick was not a quote
 * to any of them. So `` `Delete ${r.title}` `` in an `aria-label`,
 * `` `Version ${v.versionNo}` `` beside a version row, and the three
 * sentences a document upload is refused with were English on a Chinese
 * page and no gate read them -- fourteen sites across twelve screens.
 *
 * A template's copy is in the parts *between* its expressions: the text of
 * `` `Only ${exts} files can be ingested.` `` is "Only " and
 * " files can be ingested." -- the expressions are values, and a value is
 * whatever the table fills in. So the reader cuts the literal at every
 * `${...}` and reads each remaining chunk, with the same rules the text-node
 * scan uses: a capitalised phrase, or the lower-case tail of a sentence that
 * was cut around a value. The chunk after an interpolation often opens with
 * the punctuation that closed around the value -- see {@link bare}.
 *
 * One shape was still missing: the lower-case phrase with no closing mark,
 * `` ` · last touch ${formatDate(...)}` `` or `` `${n} role${plural}` ``.
 * Every rule above wants a capital or a full stop, and these have neither,
 * so a whole row's metadata -- "last touch", "added", "score", "d ago",
 * "requirements evidenced" -- printed in English on a Chinese page with the
 * gate green. {@link sentenceFragment} reads that shape.
 *
 * The expression reader tracks braces, so a nested template or an object
 * literal inside `${...}` does not end the outer literal early, and a nested
 * template is read too: its prose is as visible as the outer one's.
 *
 * The rules are deliberately the text-node rules, not the literal scan's.
 * A template is where a *label with a value in it* lives, so a single word
 * followed by a value -- `Group ${i + 1}` -- has to be read, and it is: the
 * trailing space is what makes it a phrase. A template that is entirely a
 * value -- `px-${n}` -- begins lower-case and is not prose.
 */
function readQuoted(source: string, i: number, quote: string): number {
  i++;
  while (i < source.length) {
    if (source[i] === "\\") {
      i += 2;
      continue;
    }
    if (source[i] === quote) return i + 1;
    i++;
  }
  return i;
}

interface TemplateChunk {
  text: string;
  /** The template this chunk was cut from has at least one `${...}`. */
  besideValue: boolean;
}

function readTemplate(source: string, i: number, chunks: TemplateChunk[]): number {
  const start = chunks.length;
  let chunk = "";
  let hasExpression = false;
  while (i < source.length) {
    const ch = source[i];
    if (ch === "\\") {
      chunk += ch + (source[i + 1] ?? "");
      i += 2;
      continue;
    }
    if (ch === "`") {
      chunks.push({ text: chunk, besideValue: false });
      for (let k = start; k < chunks.length; k++) chunks[k].besideValue = hasExpression;
      return i + 1;
    }
    if (ch === "$" && source[i + 1] === "{") {
      chunks.push({ text: chunk, besideValue: false });
      chunk = "";
      hasExpression = true;
      i = readTemplateExpression(source, i + 2, chunks);
      continue;
    }
    chunk += ch;
    i++;
  }
  chunks.push({ text: chunk, besideValue: false });
  for (let k = start; k < chunks.length; k++) chunks[k].besideValue = hasExpression;
  return i;
}

function readTemplateExpression(source: string, i: number, chunks: TemplateChunk[]): number {
  let depth = 1;
  while (i < source.length) {
    const ch = source[i];
    if (ch === '"' || ch === "'") {
      i = readQuoted(source, i, ch);
      continue;
    }
    if (ch === "`") {
      i = readTemplate(source, i + 1, chunks);
      continue;
    }
    if (ch === "{") {
      depth++;
      i++;
      continue;
    }
    if (ch === "}") {
      depth--;
      i++;
      if (depth === 0) return i;
      continue;
    }
    i++;
  }
  return i;
}

/** The text between the expressions of every template literal in a source. */
export function templateChunksIn(source: string): string[] {
  return templateSegmentsIn(source).map((c) => c.text);
}

function templateSegmentsIn(source: string): TemplateChunk[] {
  const chunks: TemplateChunk[] = [];
  let i = 0;
  while (i < source.length) {
    const ch = source[i];
    if (ch === '"' || ch === "'") {
      i = readQuoted(source, i, ch);
      continue;
    }
    if (ch === "`") {
      i = readTemplate(source, i + 1, chunks);
      continue;
    }
    i++;
  }
  return chunks;
}

/**
 * The lower-case phrase left between two values.
 *
 * ` · last touch ${formatDate(...)}` and `${n} role${plural}` cut a label
 * around its value: the remaining chunk opens lower-case and carries no
 * closing mark, so the head rule and the tail rule both skipped it. A
 * chunk made only of lower-case words, one of them at least three letters,
 * is that phrase -- provided the template it came from carries an
 * expression. A lone lower-case word in a template with no `${...}` is a
 * static string (a class name, a slug), and nothing about it says the
 * reader sees it in a sentence.
 *
 * What keeps the rule honest is what it refuses to strip. A separator, an
 * em dash, a comma are spacing, so they become spaces; but a hyphen, a
 * digit, a slash, a bracket or a quote is the shape of a class name, a
 * URL or a value, and any of those disqualifies the chunk outright. The
 * lower bound of three letters is what leaves a unit like `ms` alone: it is
 * one word, so it never reaches this rule anyway, and a two-letter word
 * alone (`of`, `to`) is too thin to be a label. Measured over this tree
 * when the rule was added: thirteen fragments at HEAD, every one of them
 * the words around a value on a screen, and none in a class name.
 */
function sentenceFragment(value: string): string | null {
  const words = value.replace(/[·—–,]/g, " ").replace(/\s+/g, " ").trim();
  if (!/^[a-z]+( [a-z]+)*$/.test(words)) return null;
  if (!words.split(" ").some((word) => word.length >= 3)) return null;
  return words;
}

/**
 * The chunk of a template that reads as copy, in the form the gate reports
 * it -- or null when the chunk is a value, a class name or code.
 */
function proseChunk(chunk: string, besideValue: boolean): string | null {
  const head = bare(chunk);
  if (!head) return null;
  // A phrase: it has a second word, or it ends a sentence. `Only ` is a
  // phrase because of its space; `Delete` alone is left to the scans that
  // read the positions a lone label is written in.
  //
  // The fragment rule is the exception, and only beside a value: a lone
  // lower-case word cut out of a template that carries no expression is a
  // static string -- a class name, a slug -- not half of a label. It is
  // the adjacency to `${...}` that makes the word a word around a value.
  const fragment = besideValue ? sentenceFragment(head) : null;
  if (!/\s/.test(head) && !/[.!?…]$/.test(head) && !fragment) return null;
  if (!sentenceHead(head) && !sentenceTail(head) && !fragment) return null;
  if (isCode(head)) return null;
  if (NOT_COPY.has(head.trim())) return null;
  return head.trim();
}

/** The prose in the template literals of one source, for the gate's probes. */
export function templateOffendersIn(file: string, source: string): Offender[] {
  const found: Offender[] = [];
  for (const chunk of templateSegmentsIn(stripComments(source))) {
    const value = proseChunk(chunk.text, chunk.besideValue);
    if (value) found.push({ file, attribute: "template", value });
  }
  return found;
}

function templateOffenders(): Offender[] {
  return browserSources().flatMap((rel) =>
    templateOffendersIn(rel, readFileSync(join(ROOT, rel), "utf-8"))
  );
}

/**
 * Every hardcoded string: the attributes, the object literals, the text,
 * the expressions, the literals and the templates.
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
    ...templateOffenders(),
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
