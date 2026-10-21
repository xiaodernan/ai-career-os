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
 */
export const NOT_COPY = new Set(["Career", "CareerOS", "OS"]);

/** One hardcoded copy string: the file it is in, and the string itself. */
export interface Offender {
  file: string;
  attribute: string;
  value: string;
}

/** Every `.tsx` under the browser's own source tree, tests aside. */
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
 * The filter is the interesting part. A `>` in JSX is also a comparison
 * operator, so `total > PAGE_SIZE` reads as a text node that begins with
 * "PAGE_SIZE". A candidate carrying a character that cannot appear in a
 * sentence the reader reads -- a bracket, a brace, a semicolon, an equals,
 * a pipe, another angle bracket -- is code, not copy, and is skipped.
 *
 * What this does not catch is the lowercase fragments: `} matching{" "}` is
 * the tail of a sentence whose other pieces are elsewhere, and a lone
 * word like that is not a phrase a translation key can hold. Those are a
 * known limit of the scan, not an oversight.
 */
const TEXT_NODE = /(?:>|\})([^<>{}]{1,80}?)(?=<|\{)/g;

/** A copy-bearing attribute: `title="Delete"`. */
const ATTRIBUTE = new RegExp(`\\b(${COPY_ATTRIBUTES.join("|")})="([^"\\n]+)"`, "g");

/** A copy-bearing property in an object literal: `label: "Technical"`. */
const OBJECT_LITERAL = new RegExp(`\\b(${COPY_ATTRIBUTES.join("|")}):\\s*"([^"\\n]+)"`, "g");

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

function textNodeOffenders(): Offender[] {
  const found: Offender[] = [];
  for (const rel of browserSources()) {
    const text = readFileSync(join(ROOT, rel), "utf-8");
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
      // An HTML entity inside a phrase -- "Profile & preferences" -- is
      // punctuation the reader sees, not code. It is decoded before the
      // code check so the semicolon in it does not hide the phrase.
      const decoded = value.replace(/&[a-z]+;/g, "x");
      // Code, not copy.
      if (/[(){};=<>|]/.test(decoded)) continue;
      if (NOT_COPY.has(value)) continue;
      found.push({ file: rel, attribute: "text", value });
    }
  }
  return found;
}

/** Every hardcoded string: the attributes, the object literals, the text between the tags. */
export function everyOffender(): Offender[] {
  return [...attributeOffenders(), ...objectLiteralOffenders(), ...textNodeOffenders()];
}
