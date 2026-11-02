/**
 * The words a letter's dials are written with (§12), and the third state a correction can carry.
 *
 * A kept letter stores `null` for a dial nobody set. The correction route reads a *missing* field
 * as "leave this dial alone" and an *empty string* as "clear it" -- so the drawer's "Not set"
 * option cannot travel as `""` the whole way: Radix refuses an empty `SelectItem` value, and the
 * request builder drops empty strings. It travels as `UNSET_DIAL` and becomes `""` only when the
 * request is assembled.
 */
export const UNSET_DIAL = "__unset__";

export interface CoverLetterDialOption {
  value: string;
  labelKey: string;
}

export const COVER_LETTER_TONES: CoverLetterDialOption[] = [
  { value: "balanced", labelKey: "coverLetter.tones.balanced" },
  { value: "formal", labelKey: "coverLetter.tones.formal" },
  { value: "concise", labelKey: "coverLetter.tones.concise" },
  { value: "confident", labelKey: "coverLetter.tones.confident" },
];

export const COVER_LETTER_LENGTHS: CoverLetterDialOption[] = [
  { value: "short", labelKey: "coverLetter.lengths.short" },
  { value: "standard", labelKey: "coverLetter.lengths.standard" },
  { value: "detailed", labelKey: "coverLetter.lengths.detailed" },
];

export interface LetterDials {
  tone: string;
  length: string;
}

/**
 * The options to draw for one stored value: the catalogue, plus the stored value itself when it
 * predates the catalogue. A letter kept with "warm" must not open looking like it has no tone --
 * the editor shows the word it actually carries rather than silently nothing.
 */
export function dialOptions(
  options: CoverLetterDialOption[],
  value: string
): CoverLetterDialOption[] {
  if (!value || value === UNSET_DIAL) return options;
  if (options.some((option) => option.value === value)) return options;
  return [{ value, labelKey: "" }, ...options];
}

/** Where the drawer's dials start: the value the letter was kept with, else the explicit unset. */
export function dialsOf(letter: { tone?: string | null; length?: string | null }): LetterDials {
  return { tone: letter.tone || UNSET_DIAL, length: letter.length || UNSET_DIAL };
}

/** The dials as the correction route reads them: `""` clears a dial, a value sets it. */
export function dialsToWire(dials: LetterDials): LetterDials {
  const wire = (value: string) => (value === UNSET_DIAL ? "" : value);
  return { tone: wire(dials.tone), length: wire(dials.length) };
}

/**
 * 54.1: where a kept letter sends the reader to write the next one. The job page's drafting
 * card reads `tone` and `length` off the address (and the hash scrolls to it), so the next
 * draft starts with the same dials instead of the defaults. Only catalogue values travel: a
 * stored "warm" from before the catalogue would preselect nothing on the generator, so it is
 * left out rather than sent as a value the select cannot show.
 */
export function letterRewriteHref(
  jobId: string,
  letter: { tone?: string | null; length?: string | null }
): string {
  const params = new URLSearchParams();
  if (letter.tone && COVER_LETTER_TONES.some((option) => option.value === letter.tone)) {
    params.set("tone", letter.tone);
  }
  if (letter.length && COVER_LETTER_LENGTHS.some((option) => option.value === letter.length)) {
    params.set("length", letter.length);
  }
  const query = params.toString();
  return `/jobs/${jobId}${query ? `?${query}` : ""}#cover-letter`;
}

/**
 * The dials a job page adopts from its own address. A hand-edited or stale `?tone=` must not
 * reach the generator: only values the catalogue knows are adopted, and anything else leaves
 * the default standing.
 */
export function dialSeed(search: string, fallback: LetterDials): LetterDials {
  const params = new URLSearchParams(search);
  const tone = params.get("tone");
  const length = params.get("length");
  return {
    tone: tone && COVER_LETTER_TONES.some((option) => option.value === tone) ? tone : fallback.tone,
    length:
      length && COVER_LETTER_LENGTHS.some((option) => option.value === length)
        ? length
        : fallback.length,
  };
}