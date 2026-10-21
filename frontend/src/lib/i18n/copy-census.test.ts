import { describe, expect, it } from "vitest";

import { everyOffender, browserSources, TEXT_NODE_LIMIT } from "./copy-scan";

/**
 * The browser's copy census.
 *
 * Every page and panel in this product reads its wording from one table
 * (`lib/i18n/translations.ts`), and every piece of it can be read in the
 * reader's language. That was not true a while ago, and the fix was not
 * one edit: it was about two hundred strings across thirty files, and it
 * took the discipline of a gate to keep it.
 *
 * This is that gate. The scan itself lives in `copy-scan.ts`, next to the
 * script that regenerates the list below, so the gate and the tool that
 * feeds it cannot drift apart. It finds the copy-bearing attributes that
 * still hold an English literal, the same words inside object literals, and
 * the prose between the tags. A string in any of those is a word the reader
 * cannot change, and it is the shape the fix took every time.
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
const KNOWN: Record<string, string[]> = {
  "components/ai/agent-timeline.tsx": [
    "Agent execution trace",
    "Completed",
    "Failed",
    "Running",
  ],
  "components/ai/processing-steps.tsx": [
    "AI processing progress",
  ],
  "components/ai/task-stream.tsx": [
    "Agent trace",
    "Stop following this run",
    "The run stream hasn&apos;t reported progress yet — results appear as soon as it does.",
  ],
  "components/auth/credentials-form.tsx": [
    "Account created — welcome to Career OS.",
    "Ada Zhang",
    "Already registered?",
    "Confirm password",
    "Create account",
    "Create one",
    "Create your account",
    "Email",
    "Forgot your password?",
    "Full name",
    "No account yet?",
    "Password",
    "Pick up where the agents left off.",
    "Sign in",
    "Sign in to your workspace",
    "Welcome back.",
    "Your resume becomes a knowledge base in minutes.",
  ],
  "components/jobs/analyze-jd-dialog.tsx": [
    "Analyze",
    "Analyze a JD",
    "Comparing with your resume…",
    "Hidden requirements",
    "Interview topics",
    "JD analysis",
    "Job description text",
    "Keep this text",
    "Paste a job description. The JD analyst extracts requirements, priorities and the gap\r\n            against your parsed resume.",
    "Paste the full posting — responsibilities, requirements, nice-to-haves…",
    "Preferred skills",
    "Required skills",
    "Responsibilities",
    "Resume improvement suggestions",
    "Structured output from /jds",
    "The analysis came back without structured fields. That usually means the posting text was\r\n          too short — paste the full description and run it again.",
    "Your skill gap",
  ],
  "components/jobs/import-job-dialog.tsx": [
    "Import",
    "Import a job posting",
    "Job posting text",
    "Paste a posting",
    "Paste the full posting — responsibilities, requirements, nice-to-haves…",
    "Paste the full posting. The analyst fills in the company, skills and responsibilities\r\n            and the role lands in your tracker.",
  ],
  "components/settings/memory-card.tsx": [
    "Cancel",
    "Chat with the copilot or finish an interview and the facts it learns appear here.",
    "Facts the model extracted from your conversations and interviews. Correct a wrong\r\n          one, or lower its weight — these shape every answer you get.",
    "Forget",
    "Forget this memory?",
    "High",
    "Higher-weight memories come first in every answer.",
    "It will stop shaping the answers the agents give you. This cannot be undone.",
    "Loading memories…",
    "Low",
    "Memories could not be loaded",
    "Normal",
    "Nothing remembered yet",
    "Save",
    "Weight",
    "What the agent remembers",
    "What the agents remember",
  ],
  "components/settings/profile-cards.tsx": [
    "Add row",
    "Career profile",
    "Headline",
    "Links & extras",
    "Loading profile…",
    "Location",
    "Profile could not be loaded",
    "Save maps",
    "Save profile",
    "Summary",
    "The short story a recruiter gets before the resume.",
    "What the agents assume about you — headline, targets and the story they tell recruiters.",
    "Years of experience has to be a number between 0 and",
  ],

};

describe("the browser's copy", () => {
  const found = everyOffender();

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
    // 130 files. The pin is a population, not a budget: a new file belongs
    // in it, and the count moves when one is added or removed. 129 with the
    // 404 body split out of `app/not-found.tsx` -- the page keeps its
    // `metadata` export and the localized body becomes a client component --
    // and 130 with the language switch, which the two public surfaces need.
    expect(browserSources().length).toBe(130);
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
    // The number is the census's own reading of the browser, and every one
    // of them is on the list above with a file and an owner. The pin moves
    // when a hole closes -- which is the point of pinning it.
    //
    // 131: the attributes, the object literals, the text between the tags,
    // the long sentences and the copy inside a JSX expression. The shapes
    // the scan did not read before were a third of the product's copy, and
    // the list above is the honest answer to "what have we not fixed yet".
    expect(found.length).toBe(81);
  });

  it("finds a sentence, however long it is", () => {
    // The scan's length bound was once short enough to hide most of the
    // product's prose: a sentence longer than about sixty characters sat
    // between the tags and the scan never read it. The long ones are the
    // ones that read as prose rather than as a label, so they are the
    // ones the gate is for.
    //
    // The gate is the bound itself, and the population it has to cover:
    // the longest string the census knows about has to be inside the
    // bound, or the scan would have missed it. Lowering the bound below
    // that is what let the prose hide in the first place.
    const longest = Math.max(
      ...Object.values(KNOWN).flat().map((s) => s.length)
    );
    expect(longest, "the census knows no long string, so the bound is untested").toBeGreaterThan(80);
    expect(
      TEXT_NODE_LIMIT,
      "the scan's bound is shorter than the longest string it has to read"
    ).toBeGreaterThan(longest);
  });
});
