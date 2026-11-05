/**
 * 64.1: the tags a reader types, folded into the list the note endpoint keeps.
 *
 * The form has one input, so the separator has to be forgiving: commas in either
 * language and newlines all split. Case is folded so "Interview" and "interview"
 * cannot become two chips; duplicates collapse; a tag is capped at 32 characters
 * and the list at 8, because a tag is a label rather than a document.
 */
/**
 * The tag vocabulary the interview report writes, offered as chips. A reader may
 * type any other tag too; these are the five the product itself mints, so they
 * are the ones the filter row can promise exist.
 */
export const PRODUCT_TAGS = ["interview", "study", "answer", "gap", "prepare"] as const;

/** The filter row asks for one of these or for the whole list. */
export type ProductTag = (typeof PRODUCT_TAGS)[number];

export const MAX_TAGS = 8;
export const MAX_TAG_LENGTH = 32;

export function parseTags(input: string | null | undefined): string[] {
  if (!input) return [];
  const seen = new Set<string>();
  const out: string[] = [];
  for (const raw of input.split(/[,，\n]+/)) {
    const tag = raw.trim().replace(/\s+/g, " ").toLowerCase().slice(0, MAX_TAG_LENGTH);
    if (!tag || seen.has(tag)) continue;
    seen.add(tag);
    out.push(tag);
    if (out.length === MAX_TAGS) break;
  }
  return out;
}

/**
 * 69.1: where a kept note can be read back.
 *
 * The report's four kinds of advice each carry `interview` plus their own kind
 * (`study`, `answer`, `gap`, `prepare`), and "Kept in knowledge" is only a
 * promise the reader can keep if there is a way to the note that does not
 * involve scrolling every hand-written note. The kind tag is that door: it is
 * the narrowest one the product mints, where `interview` alone opens all four
 * kinds at once. A note with no kind tag (a hand-written one, or a draft from a
 * caller that never minted one) opens the whole list rather than a filter that
 * could not match it.
 */
export const NOTES_PATH = "/knowledge";

export function noteHref(tags: readonly string[] | null | undefined): string {
  const kinds = (tags ?? []).filter((tag) => tag !== PRODUCT_TAGS[0]);
  const kind = kinds[kinds.length - 1];
  return kind ? `${NOTES_PATH}?ntag=${encodeURIComponent(kind)}` : NOTES_PATH;
}

/** The same list, written back into the one input the form offers. */
export function formatTags(tags: readonly string[] | null | undefined): string {
  return (tags ?? []).join(", ");
}
