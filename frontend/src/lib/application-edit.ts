/**
 * The application dialog's reminder math, kept out of the component so it can be tested.
 *
 * The API speaks ISO instants; the picker is a `datetime-local`, which speaks
 * `YYYY-MM-DDTHH:mm` in the browser's own timezone. Both directions of that conversion live
 * here, because that is where a timezone bug would hide: `new Date("2026-09-30T09:00")` is
 * *local* time by spec, so the value the user reads back must be rebuilt from local
 * components rather than sliced out of the ISO string.
 */

export interface ReminderPatch {
  reminderAt?: string;
  clearReminderAt?: boolean;
}

const pad = (value: number) => String(value).padStart(2, "0");

/** An ISO instant rendered as the `value` a `datetime-local` input expects (`""` if absent). */
export function toReminderInput(iso: string | null | undefined): string {
  if (!iso) return "";
  const at = new Date(iso);
  if (Number.isNaN(at.getTime())) return "";
  return (
    `${at.getFullYear()}-${pad(at.getMonth() + 1)}-${pad(at.getDate())}` +
    `T${pad(at.getHours())}:${pad(at.getMinutes())}`
  );
}

/** The inverse: picker value to ISO instant, or null when the field is empty or unparseable. */
export function fromReminderInput(value: string): string | null {
  const trimmed = value.trim();
  if (!trimmed) return null;
  const at = new Date(trimmed);
  return Number.isNaN(at.getTime()) ? null : at.toISOString();
}

/**
 * The reminder half of a PATCH body: what to say, given what the row holds and what the
 * picker now shows.
 *
 * An untouched picker contributes nothing, so the comparison is between *rendered* values —
 * two ISO spellings of one instant (`…09:00:00Z` and the `…09:00:00.000Z` the same moment
 * serialises to) would otherwise read as an edit and PATCH a no-op on every save.
 *
 * Emptying the picker is the only way to say "remove this", and it travels as
 * `clearReminderAt` rather than a null: on that DTO a null component means "leave it alone",
 * which is exactly why a set-but-never-removable reminder used to be possible.
 */
export function reminderPatch(
  currentIso: string | null | undefined,
  nextInput: string,
): ReminderPatch {
  if (toReminderInput(currentIso) === nextInput.trim()) return {};
  const next = fromReminderInput(nextInput);
  return next ? { reminderAt: next } : { clearReminderAt: true };
}

/**
 * The instant a snoozed reminder should ring: tomorrow at 09:00, local time.
 *
 * "Tomorrow morning" is a promise about the wall clock, not about twenty-four hours from now:
 * a reminder snoozed at 23:50 belongs nine hours later, not a day and ten minutes. The date is
 * advanced and the hour pinned, so the answer is always in the future — a snooze that landed
 * in the past would leave the row reading "reminder due" with nothing to press.
 */
export function snoozeReminder(now: Date = new Date()): string {
  const at = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1, 9, 0, 0, 0);
  return at.toISOString();
}
