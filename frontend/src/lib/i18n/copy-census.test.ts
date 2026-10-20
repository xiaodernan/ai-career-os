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
  "app/(app)/activity/[id]/page.tsx": [
    "Agent",
    "All activity",
    "Attribution",
    "Back to activity",
    "Cost",
    "Execution trace",
    "Finished",
    "Model",
    "Open the conversation that ran this",
    "Run id",
    "Started",
    "This run failed",
  ],
  "app/(app)/activity/page.tsx": [
    "Trace",
  ],
  "app/(app)/analysis/page.tsx": [
    "Applications at each pipeline stage.",
    "No applications have reached a stage yet.",
    "Refresh",
    "What the data says about your pipeline.",
  ],
  "app/(app)/copilot/page.tsx": [
    "Check again",
    "New chat",
    "Retry last message",
  ],
  "app/(app)/dashboard/page.tsx": [
    "All jobs",
    "Ask Copilot",
    "Avg match",
    "Browse jobs",
    "Check again",
    "Cost",
    "Detail",
    "Full log",
    "Go to Jobs",
    "Manage",
    "Open",
    "Open Copilot",
    "Open Jobs",
    "Open Networking",
    "Open board",
    "Open pipeline",
    "Prefer to talk it through?",
    "Requests",
    "Tokens",
    "Trace",
    "Upload resume",
  ],
  "app/(app)/data/page.tsx": [
    "Create",
    "Delete",
    "Total",
    "Update",
  ],
  "app/(app)/growth/page.tsx": [
    "Coverage",
    "Learning plan",
  ],
  "app/(app)/ingestion/page.tsx": [
    "Feed content",
    "Source feed",
  ],
  "app/(app)/interviews/[id]/page.tsx": [
    "All interviews",
    "Answer evaluation",
    "Finish & get report",
    "Finish early",
    "Follow-up — go deeper",
    "Loading interview…",
    "New topic",
    "Next question",
    "Open report",
    "Opening",
    "Submit answer",
    "This session so far",
  ],
  "app/(app)/interviews/[id]/report/page.tsx": [
    "All interviews",
    "Continue interview",
    "Generate report",
    "Loading report…",
    "Open",
    "Practice again",
    "What was weak",
    "What went well",
  ],
  "app/(app)/interviews/page.tsx": [
    "In progress",
    "Mode",
    "Pick a target job first",
    "Start interview",
  ],
  "app/(app)/jobs/[id]/page.tsx": [
    "Add to pipeline",
    "Back to jobs",
    "Company not researched",
    "Cover letter",
    "Interview prep",
    "Loading job…",
    "Mock interview mode",
    "Original posting",
    "Priority analysis from the JD extractor.",
    "Requirements breakdown",
    "Score from",
    "Sources",
    "Tailor resume",
    "What this page is built from.",
  ],
  "app/(app)/jobs/page.tsx": [
    "Discover",
    "Filters",
    "Note:",
    "Research roles",
    "Sort",
  ],
  "app/(app)/layout.tsx": [
    "Loading your workspace…",
  ],
  "app/(app)/monitoring/page.tsx": [
    "Latency",
    "Overall agent health assessment.",
    "Refresh",
  ],
  "app/(app)/networking/page.tsx": [
    "Draft",
  ],
  "app/(app)/offers/page.tsx": [
    "Your offer against the market, and what to say.",
  ],
  "app/(app)/rate-limit/page.tsx": [
    "Refresh",
    "Whether rate limiting is enabled.",
  ],
  "app/(app)/resumes/[id]/page.tsx": [
    "Achievements",
    "Back to resumes",
    "Current",
    "Diff vs previous",
    "Export JSON",
    "Gaps found",
    "Knowledge",
    "Loading resume…",
    "Original file",
    "Profile from",
    "Repo",
    "Set current",
  ],
  "app/(app)/resumes/page.tsx": [
    "Open",
    "Your versions",
  ],
  "app/(app)/settings/page.tsx": [
    "Account",
    "Appearance",
    "Command palette",
    "Display name",
    "Ends this session and revokes the refresh token.",
    "Keyboard",
    "Log out",
    "Save",
    "Session could not be verified.",
    "Sign out",
    "The interface follows your system theme by default.",
  ],
  "app/(auth)/layout.tsx": [
    "Career",
    "CareerOS",
    "Run your search like an engineer runs a system.",
    "The job-search operating system",
  ],
  "app/landing-page.tsx": [
    "Career",
  ],
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
  ],
  "components/auth/credentials-form.tsx": [
    "Create one",
    "Forgot your password?",
    "Sign in",
  ],
  "components/auth/reset-password-form.tsx": [
    "Request another",
    "Save new password",
  ],
  "components/common/command-palette.tsx": [
    "Promise",
  ],
  "components/copilot/artifacts.tsx": [
    "Open job",
    "Start",
    "The agent prepared a session from this conversation.",
  ],
  "components/growth/growth-engines-panel.tsx": [
    "Rehearse",
    "Study",
  ],
  "components/jobs/analyze-jd-dialog.tsx": [
    "Analyze",
    "Analyze a JD",
    "Comparing with your resume…",
    "JD analysis",
    "Job description text",
    "Keep this text",
    "Paste the full posting — responsibilities, requirements, nice-to-haves…",
    "Responsibilities",
    "Resume improvement suggestions",
    "Structured output from /jds",
  ],
  "components/jobs/import-job-dialog.tsx": [
    "Import",
    "Import a job posting",
    "Job posting text",
    "Paste a posting",
    "Paste the full posting — responsibilities, requirements, nice-to-haves…",
  ],
  "components/jobs/job-card.tsx": [
    "Found by research agent",
    "Pasted JD",
    "Why this job:",
  ],
  "components/jobs/job-filters.tsx": [
    "Company",
    "Filtering…",
    "Filters",
    "Keyword",
    "Location",
    "Remote only",
    "Salary range",
    "Skills",
  ],
  "components/jobs/match-panel.tsx": [
    "Extracted requirements, straight from the posting.",
    "Job description",
    "Nice to have",
    "Nothing fabricated here: the moment",
    "Required",
    "Resource:",
  ],
  "components/knowledge/source-actions.tsx": [
    "Clear list",
  ],
  "components/layout/sidebar.tsx": [
    "Career",
  ],
  "components/layout/topbar.tsx": [
    "Settings",
  ],
  "components/settings/memory-card.tsx": [
    "Cancel",
    "Chat with the copilot or finish an interview and the facts it learns appear here.",
    "Forget",
    "Forget this memory?",
    "Higher-weight memories come first in every answer.",
    "It will stop shaping the answers the agents give you. This cannot be undone.",
    "Loading memories…",
    "Memories could not be loaded",
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

/**
 * The text between two tags: `>Back to jobs<`.
 *
 * This is where most of the product's prose lives -- the sentences between
 * a heading and a list, the button that says "Try again". The attribute
 * scan catches the labels; this catches the sentences.
 *
 * The filter is the interesting part. A `>` in JSX is also a comparison
 * operator, so `total > PAGE_SIZE` reads as a text node that begins with
 * "PAGE_SIZE". A candidate carrying a character that cannot appear in a
 * sentence the reader reads -- a bracket, a brace, a semicolon, an equals,
 * a pipe, another angle bracket -- is code, not copy, and is skipped.
 */
const TEXT_NODE = />([^<>{}]{3,80}?)</g;

function textNodeOffenders(): Offender[] {
  const found: Offender[] = [];
  for (const rel of browserSources()) {
    const text = readFileSync(join(ROOT, rel), "utf-8");
    for (const m of text.matchAll(TEXT_NODE)) {
      const value = m[1].trim();
      if (!value) continue;
      // A sentence starts with a capital and a lower-case letter after it.
      // "AI", "OS" and "JD" are names, not sentences.
      if (!/^[A-Z][a-z]/.test(value)) continue;
      // Code, not copy.
      if (/[(){};=<>|]/.test(value)) continue;
      // An entity -- `&amp;` -- is punctuation the reader never sees.
      if (/^&[a-z]+;/.test(value)) continue;
      found.push({ file: rel, attribute: "text", value });
    }
  }
  return found;
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

/** Every hardcoded string: the copy-bearing attributes and the text nodes. */
function everyOffender(): Offender[] {
  return [...offenders(), ...textNodeOffenders()];
}

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
    // 129 files. The pin is a population, not a budget: a new file belongs
    // in it, and the count moves when one is added or removed. 129 with the
    // 404 body split out of `app/not-found.tsx` -- the page keeps its
    // `metadata` export and the localized body becomes a client component.
    expect(browserSources().length).toBe(129);
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
    // 217: the copy-bearing attributes and the text between the tags. The
    // number is the census's own reading of the browser, and every one of
    // them is on the list above with a file and an owner. The pin moves when
    // a hole closes -- which is the point of pinning it.
    expect(found.length).toBe(217);
  });
});
