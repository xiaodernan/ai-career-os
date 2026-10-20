import { describe, expect, it } from "vitest";
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative } from "node:path";
import { fileURLToPath } from "node:url";

/**
 * The browser's copy census.
 *
 * Every page and panel in this product reads its wording from one table
 * (`lib/i18n/translations.ts`), and every piece of it can be read in the
 * reader's language. That was not true a while ago, and the fix was not
 * one edit: it was about two hundred strings across thirty files, and it
 * took the discipline of a gate to keep it.
 *
 * This is that gate. It walks the browser's own sources and finds the
 * copy-bearing attributes that still hold an English literal: a `title`,
 * a `label`, a `placeholder`, an `aria-label`. A string there is a word
 * the reader cannot change, and it is the shape the fix took every time.
 *
 * The failure it catches is quiet in the worst way. A hardcoded string
 * compiles, renders, looks right in English and wrong in every other
 * language, and nothing goes red. The gate makes it red.
 *
 * `KNOWN` is the list of what is still out there, file by file, string by
 * string. It is not a budget and not a target -- it is the honest answer
 * to "what have we not fixed yet", and it shrinks as the holes close. A
 * string that is not in it is a hole the gate refuses. A string in it that
 * has since been fixed is harmless: the entry is stale, and the next
 * person to touch that file removes it.
 */

const ROOT = fileURLToPath(new URL("../../", import.meta.url));

/** The attributes that carry a word the reader sees or hears. */
const COPY_ATTRIBUTES = [
  "title",
  "description",
  "label",
  "placeholder",
  "aria-label",
  "confirmLabel",
  "ctaLabel",
  "alt",
];

/**
 * The copy still hardcoded, by file.
 *
 * Each entry is a string the file carries today. The agent-timeline and
 * processing-steps panels, the two job dialogs, the settings cards and
 * the credentials form are all mid-flight elsewhere in this repository;
 * they are listed here so the gate measures the real population instead
 * of pretending the work is finished.
 */
const KNOWN: Record<string, string[]> = {
  "components/ai/agent-timeline.tsx": ["Agent execution trace", "Running", "Completed", "Failed"],
  "components/ai/processing-steps.tsx": ["AI processing progress"],
  "components/jobs/analyze-jd-dialog.tsx": [
    "Paste the full posting — responsibilities, requirements, nice-to-haves…",
    "JD analysis",
  ],
  "components/jobs/import-job-dialog.tsx": [
    "Paste the full posting — responsibilities, requirements, nice-to-haves…",
    "https://example.com/careers/123",
  ],
  "components/settings/memory-card.tsx": [
    "Memories could not be loaded",
    "Nothing remembered yet",
    "Chat with the copilot or finish an interview and the facts it learns appear here.",
    "Forget this memory?",
    "It will stop shaping the answers the agents give you. This cannot be undone.",
    "Forget",
  ],
  "components/settings/profile-cards.tsx": [
    "Profile could not be loaded",
    "The short story a recruiter gets before the resume.",
    "value — JSON or plain text",
  ],
};

/** Every `.tsx` under the browser's own source tree, tests aside. */
function browserSources(): string[] {
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

/** One hardcoded copy string: the file it is in, and the string itself. */
interface Offender {
  file: string;
  attribute: string;
  value: string;
}

function offenders(): Offender[] {
  const found: Offender[] = [];
  const pattern = new RegExp(
    `\\b(${COPY_ATTRIBUTES.join("|")})="([^"\\n]+)"`,
    "g"
  );
  for (const rel of browserSources()) {
    const text = readFileSync(join(ROOT, rel), "utf-8");
    for (const m of text.matchAll(pattern)) {
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

describe("the browser's copy", () => {
  const found = offenders();

  it("reads its wording from the locale table, not from a literal", () => {
    // Every hardcoded string must be on the known list. A new one is a hole
    // the gate refuses -- and the message names the file and the string, so
    // the fix is obvious.
    const unlisted = found
      .filter((o) => !(KNOWN[o.file] ?? []).includes(o.value))
      .map((o) => `${o.file} ${o.attribute}="${o.value}"`);
    expect(unlisted).toEqual([]);
  });

  it("has read the whole browser by now", () => {
    // The walk itself is the thing that can silently stop: a directory that
    // moves, a suffix that changes. A census of nothing is not a census.
    //
    // 128 files. The pin is a population, not a budget: a new file belongs
    // in it, and the count moves when one is added or removed.
    expect(browserSources().length).toBe(128);
  });

  it("has a known list that names the files that still carry copy", () => {
    // The list is a population, not a wish: every file it names must still
    // be a file the walk reads, or the list has drifted out of the tree.
    for (const file of Object.keys(KNOWN)) {
      expect(browserSources(), `${file} is on the known list but not in the walk`).toContain(file);
    }
  });

  it("carries a known list that shrinks rather than grows", () => {
    // The list is a record of what is left. A file that no longer carries
    // any of its listed strings has been fixed, and the entry should go --
    // so this asserts the list is not hiding a file that is already clean.
    //
    // It is deliberately not "every listed string still exists": a string
    // that has been fixed leaves a stale entry, which is harmless, while a
    // file that has been fixed entirely should have its entry removed.
    const stale = Object.keys(KNOWN).filter(
      (file) => !found.some((o) => o.file === file)
    );
    expect(stale).toEqual([]);
  });

  it("knows how much is left", () => {
    // 17. The number is the census's own reading of the browser: down from
    // about two hundred when the work started, and every one of the
    // seventeen is on the list above with a file and an owner. The pin
    // moves when a hole closes -- which is the point of pinning it.
    expect(found.length).toBe(17);
  });
});
