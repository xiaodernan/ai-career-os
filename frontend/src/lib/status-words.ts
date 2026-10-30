/**
 * The enum words a page shows, in the reader's language.
 *
 * A stored value (`completed`, `remote`, `ai_llm`) is a wire fact, not copy. Drawing it
 * through `titleCase` produced "Completed", "Remote" and "Ai Llm" inside a Chinese page:
 * the word was assembled at render time, so the copy census could not see it and no table
 * entry existed to translate. Each roster below is the set of values its domain stores; a
 * value the table knows reads as the reader's word, and a value the roster does not know
 * keeps its English spelling rather than becoming a raw key or a blank badge.
 */
import { titleCase } from "@/lib/format";
import { INTERVIEW_MODES } from "@/lib/interview-modes";
import type { TranslateFn } from "@/lib/pipeline";

/** `agent_runs.status` — running|completed|failed|cancelled in the schema's own comment. */
export const RUN_STATUSES = ["running", "completed", "failed", "cancelled"] as const;

/** The triggers the orchestrator records; the column is open, so a stranger falls back. */
export const RUN_TRIGGERS = [
  "chat",
  "resume_parse",
  "match",
  "tailor",
  "cover_letter",
  "interview",
  "ingest",
  "nightly",
] as const;

export const JOB_STATUSES = ["open", "closed"] as const;

export const REMOTE_TYPES = ["remote", "hybrid", "onsite"] as const;

/** `resume_versions.status` — the same five words the resumes page's badge draws. */
export const RESUME_STATUSES = ["uploaded", "parsing", "ingesting", "parsed", "failed"] as const;

function wordFrom(
  t: TranslateFn,
  prefix: string,
  value: string,
  roster: readonly string[],
): string {
  if (!roster.includes(value)) return titleCase(value);
  const key = `${prefix}.${value}`;
  const word = t(key);
  return word === key ? titleCase(value) : word;
}

export function runStatusWord(t: TranslateFn, status: string): string {
  return wordFrom(t, "activity.runStatus", status, RUN_STATUSES);
}

export function runTriggerWord(t: TranslateFn, trigger: string): string {
  return wordFrom(t, "activity.trigger", trigger, RUN_TRIGGERS);
}

export function jobStatusWord(t: TranslateFn, status: string): string {
  return wordFrom(t, "jobs.status", status, JOB_STATUSES);
}

export function remoteTypeWord(t: TranslateFn, type: string): string {
  return wordFrom(t, "jobs.remoteTypes", type, REMOTE_TYPES);
}

export function resumeStatusWord(t: TranslateFn, status: string): string {
  return wordFrom(t, "resumes.status", status, RESUME_STATUSES);
}

/**
 * The mode's own name — what the two pickers list and what fills the "{mode}" slot of
 * every title. The roster's label is the fallback, the same shape `stageLabel` uses.
 */
export function interviewModeName(t: TranslateFn, mode: string): string {
  const known = INTERVIEW_MODES.find((m) => m.value === mode);
  if (!known) return titleCase(mode);
  const key = `interviews.modeNames.${mode}`;
  const word = t(key);
  return word === key ? known.label : word;
}

export function interviewModeHint(t: TranslateFn, mode: string): string {
  const known = INTERVIEW_MODES.find((m) => m.value === mode);
  if (!known) return "";
  const key = `interviews.modeHints.${mode}`;
  const hint = t(key);
  return hint === key ? known.hint : hint;
}