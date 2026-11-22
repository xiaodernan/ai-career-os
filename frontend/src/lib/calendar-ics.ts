/**
 * Epic 391 — the days you are looking at, in a file any calendar can read.
 *
 * The subscription feed (Epic 34.1 / 387) is the server's standing offer; this
 * module is the reader's one-off copy. It takes exactly the rows the grid is
 * showing — a month or a week — and writes them as all-day VEVENTs: no hour is
 * invented, no alarm rings, and a sealed letter contributes only its opening
 * day. Pure string building, so the file can be checked byte for byte in a test.
 */

import { addDays } from "@/lib/time-capsule";
import type { CalendarEvent, CalendarKind } from "@/lib/search-calendar";

export interface IcsOptions {
  /** What the receiving calendar calls this export, in the reader's own language. */
  calendarName: string;
  /** The reader's own name for each kind, from the same table the grid reads. */
  kindLabels: Record<CalendarKind, string>;
  /** One fixed instant keeps the file reproducible in a test. */
  now?: Date;
  uidDomain?: string;
}

const CRLF = "\r\n";
const MAX_OCTETS = 75;

/** RFC 5545 text: backslash, semicolon, comma and newline are the only escapes. */
export function escapeIcsText(value: string): string {
  return value
    .replace(/\\/g, "\\\\")
    .replace(/;/g, "\\;")
    .replace(/,/g, "\\,")
    .replace(/\r\n|\r|\n/g, "\\n");
}

/**
 * Fold a content line at 75 UTF-8 octets; continuations begin with one space.
 * Chinese titles are three octets a character, so a 40-character summary has to
 * fold — a naive character-count would ship a line no strict parser accepts.
 */
export function foldIcsLine(line: string): string {
  const encoder = new TextEncoder();
  const parts: string[] = [];
  let current = "";
  let octets = 0;
  for (const char of line) {
    const size = encoder.encode(char).length;
    if (octets + size > MAX_OCTETS) {
      parts.push(current);
      current = ` ${char}`;
      octets = 1 + size;
      continue;
    }
    current += char;
    octets += size;
  }
  parts.push(current);
  return parts.join(CRLF);
}

function utcStamp(date: Date): string {
  const pad = (value: number) => String(value).padStart(2, "0");
  return (
    `${date.getUTCFullYear()}${pad(date.getUTCMonth() + 1)}${pad(date.getUTCDate())}` +
    `T${pad(date.getUTCHours())}${pad(date.getUTCMinutes())}${pad(date.getUTCSeconds())}Z`
  );
}

function dateValue(date: string): string {
  return date.replace(/-/g, "");
}

/**
 * One all-day VEVENT per row, the next day exclusive as RFC 5545 requires.
 * A row whose date is unreadable never reaches this module: `buildEvents` has
 * already dropped it rather than guessed.
 */
export function buildCalendarIcs(events: CalendarEvent[], options: IcsOptions): string {
  const now = options.now ?? new Date();
  const domain = options.uidDomain ?? "ai-career-os";
  const sorted = [...events].sort((a, b) => a.date.localeCompare(b.date) || a.id.localeCompare(b.id));

  const lines: string[] = [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//AI Career OS//Calendar//EN",
    "CALSCALE:GREGORIAN",
    "METHOD:PUBLISH",
    `X-WR-CALNAME:${escapeIcsText(options.calendarName)}`,
  ];

  for (const event of sorted) {
    const label = options.kindLabels[event.kind];
    const summary = event.title ? `${label} · ${event.title}` : label;
    const end = addDays(1, new Date(`${event.date}T00:00:00`));
    lines.push(
      "BEGIN:VEVENT",
      `UID:${event.id}@${domain}`,
      `DTSTAMP:${utcStamp(now)}`,
      `DTSTART;VALUE=DATE:${dateValue(event.date)}`,
      `DTEND;VALUE=DATE:${dateValue(end)}`,
      `SUMMARY:${escapeIcsText(summary)}`
    );
    if (event.detail) lines.push(`DESCRIPTION:${escapeIcsText(event.detail)}`);
    // An all-day marker, not a meeting: the reader's calendar shows it without
    // blocking the hours and without an alarm the product never promised.
    lines.push("TRANSP:TRANSPARENT", "END:VEVENT");
  }

  lines.push("END:VCALENDAR");
  return lines.map(foldIcsLine).join(CRLF) + CRLF;
}
