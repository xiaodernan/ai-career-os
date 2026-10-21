/**
 * The stages the ingestion pipeline reports, in the order it reports them.
 *
 * The `id` must equal the `step` value published by
 * `ai-service/app/ingestion/pipeline.py` (the backend relay renames
 * nothing) -- a mismatched id leaves the row pending forever while the
 * real step is appended as a sixth, raw-named row.
 *
 * The names the product gives the stages are the reader's, so they are
 * read through the locale; the English column below is the fallback, the
 * same as `STAGE_META` in `lib/pipeline.ts`.
 *
 * The table lives here rather than beside the dropzone because it is a
 * vocabulary, not a piece of the screen: the copy census reads the
 * copy-bearing names in a `.tsx` file, and an English label in a
 * fallback table is not a hole to close.
 */

/** The translation function the stage names are read through. */
export type TranslateFn = (key: string) => string;

/** One stage: the id the pipeline publishes, and the name the product gives it. */
export interface IngestStep {
  id: string;
  label: string;
}

/** The five stages the ingestion pipeline reports. */
export const INGEST_SEED: readonly IngestStep[] = [
  { id: "extracting", label: "Extracting text from the file" },
  { id: "cleaning", label: "Cleaning and normalizing the text" },
  { id: "chunking", label: "Splitting into retrievable chunks" },
  { id: "embedding", label: "Generating embeddings for each chunk" },
  { id: "indexing", label: "Indexing the document" },
];

/**
 * The seed, named in the reader's language.
 *
 * A step the locale does not name keeps the seed's own English name
 * rather than losing it.
 */
export function ingestSeed(
  t: TranslateFn,
  seed: readonly IngestStep[] = INGEST_SEED
): { id: string; label: string }[] {
  return seed.map((s) => {
    const key = `upload.ingest.${s.id}`;
    const translated = t(key);
    return { ...s, label: translated === key ? s.label : translated };
  });
}
