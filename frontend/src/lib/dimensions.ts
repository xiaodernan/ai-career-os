/**
 * The score dimensions the product names, and how they are named.
 *
 * Three surfaces draw the same kind of bar -- the match panel, the copilot's
 * match artifact, and the interview report -- and each of them was carrying
 * its own English labels. The copy census cannot see them: it reads the
 * copy-bearing *attributes* and the *text between the tags* of a `.tsx` file,
 * and these were neither. A `label: "Technical"` inside an object literal is
 * a word the reader cannot change, and it is exactly as invisible to the
 * gate as an attribute was.
 *
 * So the vocabulary lives here, in one place, and every surface reads it
 * through the locale. The keys are the wire's own -- `technical`,
 * `technical_accuracy`, `bullets` -- because that is what the services
 * answer with, and a name of our own would be a second spelling to keep in
 * step.
 *
 * The three vocabularies are separate, and each has its own namespace
 * because two of them share a key: a *structure* in an interview answer is
 * not a *structure* in a resume. One flat table would answer both with the
 * same word, and the reader would be looking at the wrong one.
 */

/** The translation function the dimension names are read through. */
export type TranslateFn = (key: string) => string;

/** One vocabulary: a wire key and the English name the product gives it. */
export interface DimensionVocabulary {
  key: string;
  label: string;
}

/**
 * The match's four dimensions.
 *
 * These are the columns `compute_match` writes and `MatchSummary` stores
 * (`_overall(technical, experience, projects, education)` in the ai-service),
 * so the keys are the wire's and the labels are ours.
 */
export const MATCH_DIMENSIONS: readonly DimensionVocabulary[] = [
  { key: "technical", label: "Technical" },
  { key: "experience", label: "Experience" },
  { key: "projects", label: "Projects" },
  { key: "education", label: "Education" },
];

/**
 * The interview's eight dimensions.
 *
 * The list is the ai-service's `DIMENSIONS` in `app/features/interview.py`,
 * and the evaluator grades on the first four of them per answer while a
 * finalized report carries all eight.
 */
export const INTERVIEW_DIMENSIONS: readonly DimensionVocabulary[] = [
  { key: "technical_accuracy", label: "Technical accuracy" },
  { key: "communication", label: "Communication" },
  { key: "depth", label: "Depth" },
  { key: "structure", label: "Structure" },
  { key: "problem_solving", label: "Problem solving" },
  { key: "system_thinking", label: "System thinking" },
  { key: "ai_knowledge", label: "AI knowledge" },
  { key: "backend_knowledge", label: "Backend knowledge" },
];

/** The resume reviewer's five rubric dimensions. */
export const RESUME_DIMENSIONS: readonly DimensionVocabulary[] = [
  { key: "bullets", label: "Bullets & metric density" },
  { key: "structure", label: "Structure & scannability" },
  { key: "impact", label: "Impact wording" },
  { key: "clarity", label: "Clarity" },
  { key: "keywords", label: "Keyword coverage" },
];

/** The rubric's unmet criteria, named in the reader's language. */
export const RESUME_CRITERIA: readonly DimensionVocabulary[] = [
  { key: "has_contact", label: "Contact info (email / phone)" },
  { key: "has_summary", label: "A summary section" },
  { key: "has_experience", label: "Work experience" },
  { key: "experience_has_bullets", label: "Bullets under your roles" },
  { key: "quantified_impact", label: "Quantified impact (numbers or %)" },
  { key: "has_projects", label: "Projects" },
  { key: "has_education", label: "Education" },
  { key: "has_skills", label: "Enough skills (5+)" },
  { key: "years_experience_stated", label: "Stated years of experience" },
  { key: "dates_present", label: "Start dates on all roles" },
];

/**
 * The name a dimension is given, in the reader's language.
 *
 * The table is the fallback: a dimension the locale does not name keeps the
 * product's own English name rather than losing it, which is the same rule
 * `stageLabel` in `lib/pipeline.ts` follows for the pipeline's seven stages.
 * A key no vocabulary knows keeps the name the wire gave it -- the reader
 * sees `technical_accuracy` rather than a blank bar.
 */
export function dimensionLabel(
  t: TranslateFn,
  namespace: string,
  vocabulary: readonly DimensionVocabulary[],
  key: string
): string {
  const known = vocabulary.find((d) => d.key === key);
  if (!known) return key.replace(/_/g, " ");
  const translationKey = `dimensions.${namespace}.${known.key}.label`;
  const translated = t(translationKey);
  return translated === translationKey ? known.label : translated;
}

/** The match panel's four names, in the reader's language. */
export function matchDimensionLabel(t: TranslateFn, key: string): string {
  return dimensionLabel(t, "match", MATCH_DIMENSIONS, key);
}

/** The interview rubric's eight names, in the reader's language. */
export function interviewDimensionLabel(t: TranslateFn, key: string): string {
  return dimensionLabel(t, "interview", INTERVIEW_DIMENSIONS, key);
}

/** The resume reviewer's five names, in the reader's language. */
export function resumeDimensionLabel(t: TranslateFn, key: string): string {
  return dimensionLabel(t, "resume", RESUME_DIMENSIONS, key);
}

/** The rubric's unmet criteria, in the reader's language. */
export function resumeCriterionLabel(t: TranslateFn, key: string): string {
  return dimensionLabel(t, "criteria", RESUME_CRITERIA, key);
}
