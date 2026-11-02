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
