import { describe, expect, it } from "vitest";

import { buildAgendaText } from "@/lib/calendar-agenda";
import type { CalendarEvent } from "@/lib/search-calendar";

const LABELS = {
  reminder: "Reminder",
  followup: "Follow-up due",
  interview: "Rehearsal",
  offer: "Offer deadline",
  capsule: "Sealed letter opens",
};

const OPTIONS = {
  title: "Career search · September 2026",
  locale: "en" as const,
  kindLabels: LABELS,
  emptyTitle: "A letter to your future self",
};

function row(overrides: Partial<CalendarEvent> = {}): CalendarEvent {
  return {
    id: "a",
    date: "2026-09-20",
    kind: "reminder",
    title: "Backend Engineer",
    ...overrides,
  };
}

/**
 * Epic 412 — the agenda is a file the reader pastes somewhere else, so its
 * shape is the test: a heading, a day heading with its weekday, and one bullet
 * per row carrying the row's own words.
 */
describe("the calendar as an agenda", () => {
  it("groups rows under their day and keeps the order the grid draws", () => {
    const text = buildAgendaText(
      [
        row({ id: "1", date: "2026-09-20", title: "Backend Engineer", detail: "Acme Robotics" }),
        row({ id: "2", date: "2026-09-20", kind: "offer", title: "Lunar Works" }),
        row({ id: "3", date: "2026-09-21", kind: "interview", title: "Staff Engineer" }),
      ],
      OPTIONS
    );
    expect(text).toBe(
      [
        "Career search · September 2026",
        "",
        "Sep 20, 2026 · Sun",
        "- Reminder · Backend Engineer · Acme Robotics",
        "- Offer deadline · Lunar Works",
        "",
        "Sep 21, 2026 · Mon",
        "- Rehearsal · Staff Engineer",
      ].join("\n")
    );
  });

  it("carries the door when a web root is given, and never a double slash", () => {
    const text = buildAgendaText(
      [row({ href: "/applications?application=app-1" })],
      { ...OPTIONS, webRoot: "https://career.example.com/" }
    );
    expect(text).toContain("- Reminder · Backend Engineer https://career.example.com/applications?application=app-1");
  });

  it("names an untitled row rather than leaving a bullet empty", () => {
    const text = buildAgendaText(
      [row({ kind: "capsule", title: "", href: undefined })],
      { ...OPTIONS, webRoot: "https://career.example.com" }
    );
    expect(text).toContain("- Sealed letter opens · A letter to your future self");
    expect(text).not.toContain("A letter to your future self https://");
  });

  it("writes nothing at all when there is nothing on the grid", () => {
    expect(buildAgendaText([], OPTIONS)).toBe("");
  });

  it("speaks Chinese, weekday and all", () => {
    const text = buildAgendaText([row()], {
      ...OPTIONS,
      title: "求职日历 · 2026年9月",
      locale: "zh",
      kindLabels: {
        reminder: "提醒",
        followup: "该跟进了",
        interview: "模拟面试",
        offer: "录用截止日",
        capsule: "封存的信开启",
      },
      emptyTitle: "一封写给未来自己的信",
    });
    expect(text).toContain("2026年9月20日 · 周日");
    expect(text).toContain("- 提醒 · Backend Engineer");
  });
});
