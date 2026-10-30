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
import { formatSalary, titleCase } from "@/lib/format";
import { INTERVIEW_MODES } from "@/lib/interview-modes";
import type { TranslateFn } from "@/lib/pipeline";
import { TRACE_KINDS } from "@/lib/trace-kinds";

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

/**
 * `knowledge_sources.status` — the default `pending`, the ingest service's
 * `ingesting`/`failed`, and the `ready` the ai-service's ready callback writes.
 */
export const KNOWLEDGE_SOURCE_STATUSES = ["pending", "ingesting", "ready", "failed"] as const;

/** `monitoring.py`'s health verdict, and the word the page shows when the report has none. */
export const HEALTH_VERDICTS = ["healthy", "warn", "regressed", "unknown"] as const;

/** `readiness.py`'s coverage verdict, and the page's fallback for a missing one. */
export const READINESS_VERDICTS = ["ready", "borderline", "not_ready", "unknown"] as const;

/** `negotiation.py`'s market position, and the assessment's own "unknown". */
export const MARKET_VERDICTS = ["below_market", "above_market", "within_market", "unknown"] as const;

/**
 * The JD's priority word. `jd_analyze.py` writes must|should|nice on every
 * requirement, and `match.py` copies the requirement's own word onto each
 * skill gap, so the requirements badge and the gap badge draw one vocabulary.
 */
export const REQUIREMENT_PRIORITIES = ["must", "should", "nice"] as const;

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

export function healthVerdictWord(t: TranslateFn, verdict: string): string {
  return wordFrom(t, "monitoring.verdicts", verdict, HEALTH_VERDICTS);
}

export function readinessVerdictWord(t: TranslateFn, verdict: string): string {
  return wordFrom(t, "growth.verdicts", verdict, READINESS_VERDICTS);
}

export function marketVerdictWord(t: TranslateFn, verdict: string): string {
  return wordFrom(t, "offers.verdicts", verdict, MARKET_VERDICTS);
}

export function requirementPriorityWord(t: TranslateFn, priority: string): string {
  return wordFrom(t, "jobs.detail.priorities", priority, REQUIREMENT_PRIORITIES);
}

export function knowledgeSourceStatusWord(t: TranslateFn, status: string): string {
  return wordFrom(t, "knowledge.sources.statuses", status, KNOWLEDGE_SOURCE_STATUSES);
}

/** The trace row's kind badge; the roster is the transport's own gate (`asTraceKind`). */
export function traceKindWord(t: TranslateFn, kind: string): string {
  return wordFrom(t, "ai.agentTimeline.kinds", kind, TRACE_KINDS);
}

/**
 * The seniority chip's words, from the reader's table.
 *
 * `jobs.experience_years` is a number on the wire; the mapper used to turn it into the
 * English phrase ("3+ years experience", "Entry level") before any page saw it, so the
 * sentence could not be translated and the copy census could not see it. 0 stays a real
 * answer ("entry level"), and the two English plurals need two keys — `1+ year` is not
 * `1+ years`.
 */
type SentenceFn = (key: string, vars?: Record<string, string | number>) => string;

export function seniorityWord(t: SentenceFn, years: number): string {
  if (years === 0) return t("jobs.detail.entryLevel");
  return t(years === 1 ? "jobs.detail.experienceYear" : "jobs.detail.experienceYears", { years });
}

/**
 * The salary band's sentence, read from the table.
 *
 * `formatSalary` formats the amount but cannot speak for a reader; its ceiling branch
 * used to say "up to" in every language. A page draws a stored band through this call,
 * which hands the table's sentence for the ceiling and leaves the amounts alone.
 */
export function salaryBandWord(
  t: SentenceFn,
  min?: number | null,
  max?: number | null,
  currency?: string | null
): string | null {
  return formatSalary(min, max, currency, (amount) => t("jobs.salaryUpTo", { amount }));
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