import { describe, expect, it } from "vitest";

import { buildCalendarIcs, escapeIcsText, foldIcsLine } from "@/lib/calendar-ics";
import type { CalendarEvent, CalendarKind } from "@/lib/search-calendar";

/**
 * Epic 391 — the file the reader takes away. Every expectation below is a line
 * a calendar app will actually parse: CRLF, an all-day DTSTART/DTEND pair, the
 * five RFC escapes, folded at 75 octets, and never a sealed letter's body.
 */

const LABELS: Record<CalendarKind, string> = {
  reminder: "Reminder",
  followup: "Follow-up due",
  interview: "Rehearsal",
  offer: "Offer deadline",
  capsule: "Sealed letter opens",
};

const NOW = new Date(Date.UTC(2026, 10, 22, 12, 0, 0));

function event(overrides: Partial<CalendarEvent> = {}): CalendarEvent {
  return {
    id: "reminder-app-1",
    date: "2026-09-20",
    kind: "reminder",
    title: "Backend Engineer",
    detail: "Acme Robotics",
    href: "/applications?application=app-1",
    ...overrides,
  };
}

function build(events: CalendarEvent[]): string {
  return buildCalendarIcs(events, { calendarName: "Career search", kindLabels: LABELS, now: NOW });
}

describe("the calendar file", () => {
  it("opens and closes a published calendar with CRLF everywhere", () => {
    const ics = build([event()]);
    expect(ics.startsWith("BEGIN:VCALENDAR\r\n")).toBe(true);
    expect(ics.endsWith("END:VCALENDAR\r\n")).toBe(true);
    expect(ics).toContain("VERSION:2.0\r\n");
    expect(ics).toContain("METHOD:PUBLISH\r\n");
    expect(ics).toContain("X-WR-CALNAME:Career search\r\n");
    // No bare LF survives: a mail or calendar client may treat it as a broken line.
    expect(ics.replace(/\r\n/g, "")).not.toContain("\n");
  });

  it("writes one all-day event on the row's own day, next day exclusive", () => {
    const ics = build([event()]);
    expect(ics).toContain("BEGIN:VEVENT\r\n");
    expect(ics).toContain("END:VEVENT\r\n");
    expect(ics).toContain("UID:reminder-app-1@ai-career-os\r\n");
    expect(ics).toContain("DTSTAMP:20261122T120000Z\r\n");
    expect(ics).toContain("DTSTART;VALUE=DATE:20260920\r\n");
    expect(ics).toContain("DTEND;VALUE=DATE:20260921\r\n");
    expect(ics).toContain("SUMMARY:Reminder · Backend Engineer\r\n");
    expect(ics).toContain("DESCRIPTION:Acme Robotics\r\n");
    expect(ics).toContain("TRANSP:TRANSPARENT\r\n");
    // An all-day row gets no alarm, because the product never promised one.
    expect(ics).not.toContain("BEGIN:VALARM");
  });

  it("carries a row with no detail and a sealed letter with no prose", () => {
    const ics = build([
      event({ id: "followup-c-1", kind: "followup", title: "Ada Byron", detail: undefined }),
      event({ id: "capsule-n-1", kind: "capsule", title: "", detail: undefined }),
    ]);
    expect(ics).toContain("SUMMARY:Follow-up due · Ada Byron\r\n");
    expect(ics).not.toContain("DESCRIPTION:\r\n");
    expect(ics).toContain("SUMMARY:Sealed letter opens\r\n");
    expect(ics).not.toContain("a secret plan");
  });

  it("escapes the five characters RFC 5545 reserves", () => {
    expect(escapeIcsText("a\\b;c,d\ne")).toBe("a\\\\b\\;c\\,d\\ne");
    const ics = build([event({ title: "R&D; platform, core", detail: "line one\nline two" })]);
    // The comma in the summary is escaped, so the line still reads as one text value.
    expect(ics).toContain("SUMMARY:Reminder · R&D\\; platform\\, core\r\n");
    expect(ics).toContain("DESCRIPTION:line one\\nline two\r\n");
  });

  it("folds long Chinese summaries at 75 octets and unfolds back to one line", () => {
    const title = "后端平台工程师".repeat(8);
    const ics = build([event({ title })]);
    const summaryLines = ics
      .split("\r\n")
      .filter((line) => line.startsWith("SUMMARY:") || line.startsWith(" "));
    expect(summaryLines.length).toBeGreaterThan(1);
    for (const line of summaryLines) {
      expect(new TextEncoder().encode(line).length).toBeLessThanOrEqual(75);
    }
    // A continuation line begins with one space; unfold and the sentence is whole.
    const joined = ics
      .replace(/\r\n /g, "")
      .split("\r\n")
      .find((line) => line.startsWith("SUMMARY:"));
    expect(joined).toBe(`SUMMARY:Reminder · ${title}`);

    expect(foldIcsLine("short")).toBe("short");
    expect(foldIcsLine("x".repeat(80)).split("\r\n")).toHaveLength(2);
  });

  it("keeps the way back to the row when it is given an origin", () => {
    const withRoot = buildCalendarIcs([event()], {
      calendarName: "Career search",
      kindLabels: LABELS,
      now: NOW,
      webRoot: "https://career.example/",
    });
    expect(withRoot).toContain("URL:https://career.example/applications?application=app-1\r\n");
    // Without an origin the file stays self-contained rather than carrying a dead relative link.
    expect(build([event()])).not.toContain("URL:");
    const noDoor = buildCalendarIcs([event({ href: undefined })], {
      calendarName: "Career search",
      kindLabels: LABELS,
      now: NOW,
      webRoot: "https://career.example",
    });
    expect(noDoor).not.toContain("URL:");
  });

  it("sorts by day then id so two downloads of the same grid are identical", () => {
    const ics = build([
      event({ id: "b", date: "2026-09-21" }),
      event({ id: "a", date: "2026-09-20" }),
      event({ id: "c", date: "2026-09-20" }),
    ]);
    const uids = [...ics.matchAll(/^UID:(.+)$/gm)].map((match) => match[1]);
    expect(uids).toEqual(["a@ai-career-os", "c@ai-career-os", "b@ai-career-os"]);
    expect(build([]).match(/BEGIN:VEVENT/g)).toBeNull();
  });
});
