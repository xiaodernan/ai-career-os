/**
 * The kinds a knowledge source may have.
 *
 * The values are the wire's -- `KnowledgeService.KINDS`, which
 * `validateKind` rejects anything else from, and the backend's
 * `validateKind` is a 400 for a value it does not name. The names the
 * product gives them are the reader's, so they are read through the
 * locale.
 *
 * The table lives here rather than beside the uploader because it is a
 * vocabulary, not a piece of the screen: the copy census reads the
 * copy-bearing names in a `.tsx` file, and an English label in a
 * fallback table is not a hole to close -- it is the table's own
 * English column, the same as `STAGE_META` in `lib/pipeline.ts`. Keeping
 * the vocabulary in a `.ts` module is what says so.
 */

/** The translation function the kind names are read through. */
export type TranslateFn = (key: string) => string;

/** One kind: the value the wire names, and the name the product gives it. */
export interface SourceKind {
  value: string;
  label: string;
}

/** The nine kinds a source may have, in the order the selector offers them. */
export const SOURCE_KINDS: readonly SourceKind[] = [
  { value: "note", label: "Note" },
  { value: "resume", label: "Resume" },
  { value: "project", label: "Project" },
  { value: "jd", label: "Job description" },
  { value: "company", label: "Company" },
  { value: "interview_feedback", label: "Interview feedback" },
  { value: "certificate", label: "Certificate" },
  { value: "course", label: "Course" },
  { value: "goal", label: "Goal" },
];

/**
 * The kind's name, in the reader's language.
 *
 * A kind the locale does not name keeps the product's own English name
 * rather than losing it, which is the rule `stageLabel` in
 * `lib/pipeline.ts` follows for the pipeline's seven stages.
 */
export function sourceKindLabel(t: TranslateFn, value: string): string {
  const known = SOURCE_KINDS.find((k) => k.value === value);
  if (!known) return value;
  const key = `knowledge.sources.kinds.${value}`;
  const translated = t(key);
  return translated === key ? known.label : translated;
}
