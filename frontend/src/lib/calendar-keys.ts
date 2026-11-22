/**
 * Epic 394 — the calendar answers the keyboard.
 *
 * A reader who plans in days often has one hand on the arrows already. This
 * module is the whole decision: which key means which walk, and when a key is
 * not ours at all. It stays pure so the rule can be checked without a browser:
 * a key pressed inside a text field belongs to the field, and a modified key
 * belongs to the browser or the command palette.
 */

export type CalendarNavAction = "prev" | "next" | "today" | "find";

export interface CalendarKeyContext {
  /** True while the reader is typing in an input, textarea, select or editable region. */
  inField?: boolean;
  /** True when any of Meta, Ctrl or Alt is held: a shortcut, not a stride. */
  modifier?: boolean;
}

export function calendarNavFromKey(
  key: string,
  context: CalendarKeyContext = {}
): CalendarNavAction | null {
  if (context.inField || context.modifier) return null;
  if (key === "ArrowLeft") return "prev";
  if (key === "ArrowRight") return "next";
  if (key === "t" || key === "T") return "today";
  // Epic 409 — the same key the web uses for "find on this page" now opens the
  // calendar's own find box, because that is the one search this page owns.
  if (key === "/") return "find";
  return null;
}
