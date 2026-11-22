/**
 * Epic 396 — a prompt for the sealed letter.
 *
 * The capsule composer asks for a letter to the future; the hardest part is the
 * first sentence. These ten prompts rotate by the reader's own calendar day, so
 * everyone opening the card on the same day sees the same invitation, and a
 * reader can step to the next one without waiting. Pure arithmetic over a date,
 * no network and no model.
 */

export const CAPSULE_PROMPT_KEYS = [
  "timeline.capsulePrompt1",
  "timeline.capsulePrompt2",
  "timeline.capsulePrompt3",
  "timeline.capsulePrompt4",
  "timeline.capsulePrompt5",
  "timeline.capsulePrompt6",
  "timeline.capsulePrompt7",
  "timeline.capsulePrompt8",
  "timeline.capsulePrompt9",
  "timeline.capsulePrompt10",
] as const;

/** The day's index into the prompt list; `offset` steps forward or back without wrapping wrong. */
export function capsulePromptIndex(date: Date = new Date(), offset: number = 0): number {
  const days = Math.floor(
    Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()) / 86_400_000
  );
  const size = CAPSULE_PROMPT_KEYS.length;
  return (((days + offset) % size) + size) % size;
}

export function capsulePromptKey(date: Date = new Date(), offset: number = 0): string {
  return CAPSULE_PROMPT_KEYS[capsulePromptIndex(date, offset)];
}
