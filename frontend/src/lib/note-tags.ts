/**
 * 64.1: the tags a reader types, folded into the list the note endpoint keeps.
 *
 * The form has one input, so the separator has to be forgiving: commas in either
 * language and newlines all split. Case is folded so "Interview" and "interview"
 * cannot become two chips; duplicates collapse; a tag is capped at 32 characters
 * and the list at 8, because a tag is a label rather than a document.
 */
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

/** The same list, written back into the one input the form offers. */
export function formatTags(tags: readonly string[] | null | undefined): string {
  return (tags ?? []).join(", ");
}
