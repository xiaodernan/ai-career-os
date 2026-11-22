/**
 * Epic 412 — the calendar as plain text. The grid and the ICS file both leave
 * the app, but neither is something a reader can paste into a note, a message
 * or a stand-up update. This fold turns the rows already on screen into an
 * agenda: one heading, one line per day, one bullet per row, in the reader's
 * own language and the order the grid already draws.
 *
 * It is pure arithmetic over `CalendarEvent[]` — no endpoint, no model call,
 * no reading of a clock. A row with no title falls back to the caller's own
 * word for it rather than inventing one; an empty list produces no text at all,
 * because a copied file with a title and nothing under it is not an agenda.
 */

import { formatDateOnly } from "@/lib/format";
import type { Locale } from "@/lib/i18n/translations";
import type { CalendarEvent, CalendarKind } from "@/lib/search-calendar";

export interface AgendaOptions {
  /** The first line — the calendar's name and the range it covers. */
  title: string;
  locale: Locale;
  kindLabels: Record<CalendarKind, string>;
  /** What an untitled row (a sealed letter) is called in the reader's language. */
  emptyTitle: string;
  /** When given, each row with a door also carries its absolute address. */
  webRoot?: string;
}

/** "Sun" / "周日" — a short weekday for the day heading. */
function weekdayName(date: string, locale: Locale): string {
  return new Intl.DateTimeFormat(locale === "zh" ? "zh-CN" : "en-US", { weekday: "short" }).format(
    new Date(`${date}T00:00:00`)
  );
}

export function buildAgendaText(events: CalendarEvent[], options: AgendaOptions): string {
  if (events.length === 0) return "";
  const root = options.webRoot ? options.webRoot.replace(/\/+$/, "") : "";
  const lines: string[] = [options.title];
  let day = "";
  for (const event of events) {
    if (event.date !== day) {
      day = event.date;
      lines.push("");
      lines.push(`${formatDateOnly(event.date, options.locale)} · ${weekdayName(event.date, options.locale)}`);
    }
    const parts = [options.kindLabels[event.kind], event.title || options.emptyTitle];
    if (event.detail) parts.push(event.detail);
    const link = root && event.href ? ` ${root}${event.href}` : "";
    lines.push(`- ${parts.join(" · ")}${link}`);
  }
  return lines.join("\n").trim();
}
