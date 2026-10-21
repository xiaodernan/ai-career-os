/**
 * The growth engines, and how they are named.
 *
 * Nine engines, each with a name the reader sees in two places: the button
 * that picks the engine, and the button that runs it ("Run Gap analysis").
 * The names used to be English literals in the panel's own table -- an
 * object literal, which the copy census cannot read, because it walks the
 * copy-bearing attributes and the text between the tags of a `.tsx` file
 * and nothing else. A Chinese reader was choosing between nine English
 * names.
 *
 * The names live here now, and the panel reads them through the locale.
 * The key is the engine's own, so the table can be read without a provider
 * mounted and an unknown engine keeps a name rather than losing it.
 */

/** The translation function the engine names are read through. */
export type TranslateFn = (key: string) => string;

/** One engine: its key, its name, and the epic it came from. */
export interface GrowthEngine {
  key: string;
  label: string;
  epic: string;
}

/**
 * The nine engines, in the order the panel offers them.
 *
 * The epic numbers are the roadmap's, and they are here because the panel
 * shows which epic an engine belongs to -- a number, not a word, so it does
 * not need a translation.
 */
export const GROWTH_ENGINES: readonly GrowthEngine[] = [
  { key: "gap", label: "Gap analysis", epic: "10.1" },
  { key: "demand", label: "Market demand", epic: "10.9" },
  { key: "priority", label: "Learning priority", epic: "10.12" },
  { key: "plan", label: "Learning plan", epic: "10.5" },
  { key: "prep", label: "Interview prep", epic: "10.13" },
  { key: "progression", label: "Progression", epic: "10.11" },
  { key: "stories", label: "Story bank", epic: "6.5" },
  { key: "roles", label: "Role suggestions", epic: "10.10" },
  { key: "progress", label: "Progress", epic: "10.6" },
];

/**
 * The engine's name, in the reader's language.
 *
 * An engine the locale does not name keeps the product's own English name
 * rather than losing it, which is the same rule `stageLabel` in
 * `lib/pipeline.ts` follows for the pipeline's seven stages.
 */
export function growthEngineLabel(t: TranslateFn, key: string): string {
  const known = GROWTH_ENGINES.find((e) => e.key === key);
  if (!known) return key;
  const translationKey = `growthEngines.engines.${key}`;
  const translated = t(translationKey);
  return translated === translationKey ? known.label : translated;
}
