import { describe, expect, it } from "vitest";

import {
  buildEvents,
  dateKeyOf,
  eventsInMonth,
  followUpDue,
  monthCells,
  monthKeyOf,
  nextEvent,
  readMonthKey,
  shiftMonth,
  summarize,
} from "@/lib/search-calendar";
import type { Application, FollowUpItem, InterviewSession, KnowledgeNote } from "@/lib/api/types";

/**
 * Epic 386 — the month is arithmetic over rows the page already holds. Every
 * expectation below can be checked against a wall calendar: Monday-first weeks,
 * 42 cells, local dates, and a follow-up due exactly one cadence after its touch.
 */
const TODAY = "2026-09-15";

function application(overrides: Partial<Application> = {}): Application {
  return {
    id: "app-1",
    title: "Backend Engineer",
    companyName: "Acme Robotics",
    status: "applied",
    reminderAt: "2026-09-20T09:00:00Z",
    ...overrides,
  };
}

function interview(overrides: Partial<InterviewSession> = {}): InterviewSession {
  return {
    id: "int-1",
    mode: "technical",
    status: "completed",
    jobTitle: "Staff Engineer",
    companyName: "Lunar Works",
    startedAt: "2026-09-10T10:00:00Z",
    ...overrides,
  };
}

function followUp(overrides: Partial<FollowUpItem> = {}): FollowUpItem {
  return { id: "c-1", name: "Ada Byron", company: "Analytical Engines", daysSince: 10, cadenceDays: 7, ...overrides };
}

function capsule(tags: string[], content = "a secret plan"): KnowledgeNote {
  return { id: "n-1", title: "", content, tags };
}

describe("the month grid", () => {
  it("reads a month only when it is one", () => {
    expect(readMonthKey("2026-09")).toBe("2026-09");
    expect(readMonthKey("2026-13")).toBeNull();
    expect(readMonthKey("2026-9")).toBeNull();
    expect(readMonthKey("")).toBeNull();
  });

  it("shifts months across a year boundary in both directions", () => {
    expect(shiftMonth("2026-12", 1)).toBe("2027-01");
    expect(shiftMonth("2026-01", -1)).toBe("2025-12");
    expect(shiftMonth("2026-09", 0)).toBe("2026-09");
  });

  it("always draws six Monday-first weeks and flags the month's own days", () => {
    const september = monthCells("2026-09");
    expect(september.length).toBe(42);
    // 2026-09-01 is a Tuesday, so the grid opens on Monday 2026-08-31.
    expect(september[0]).toEqual({ date: "2026-08-31", inMonth: false });
    expect(september[1]).toEqual({ date: "2026-09-01", inMonth: true });
    expect(september.filter((cell) => cell.inMonth).length).toBe(30);

    const leap = monthCells("2024-02");
    expect(leap.filter((cell) => cell.inMonth).length).toBe(29);
  });

  it("opens every month it draws on a Monday", () => {
    for (const key of ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06"]) {
      const first = monthCells(key)[0];
      expect(new Date(`${first.date}T00:00:00`).getDay()).toBe(1);
    }
  });

  it("drops an unreadable instant rather than guessing a day", () => {
    expect(dateKeyOf("not a date")).toBeNull();
    expect(dateKeyOf(null)).toBeNull();
    expect(dateKeyOf("2026-09-20T09:00:00Z")).toMatch(/^2026-09-(20|21)$/);
  });

  it("names the current month in the reader's own clock", () => {
    expect(monthKeyOf(new Date(2026, 8, 15))).toBe("2026-09");
  });
});

describe("buildEvents", () => {
  it("puts an application's reminder on its day and ignores rows without one", () => {
    const events = buildEvents({
      applications: [application(), application({ id: "app-2", reminderAt: null })],
      today: TODAY,
    });
    expect(events).toHaveLength(1);
    expect(events[0]).toMatchObject({
      id: "reminder-app-1",
      kind: "reminder",
      title: "Backend Engineer",
      detail: "Acme Robotics",
      href: "/applications?application=app-1",
    });
    expect(events[0].date).toMatch(/^2026-09-(20|21)$/);
  });

  it("puts a rehearsal on the day it started", () => {
    const events = buildEvents({ interviews: [interview()], today: TODAY });
    expect(events[0]).toMatchObject({
      id: "interview-int-1",
      kind: "interview",
      title: "Staff Engineer",
      href: "/interviews/int-1",
    });
  });

  it("puts a follow-up on the day its cadence runs out, including overdue ones", () => {
    expect(followUpDue(followUp(), TODAY)).toBe("2026-09-12");
    const events = buildEvents({ followUps: [followUp()], today: TODAY });
    expect(events[0].date).toBe("2026-09-12");
    expect(events[0].href).toBe("/networking");
    // Without a cadence there is no due day: the row is dropped, not invented.
    expect(followUpDue(followUp({ cadenceDays: null }), TODAY)).toBeNull();
  });

  it("puts a sealed letter on its opening day and never carries its prose", () => {
    const events = buildEvents({ notes: [capsule(["capsule", "capsule-2026-09-25"])], today: TODAY });
    expect(events).toHaveLength(1);
    expect(events[0]).toMatchObject({ date: "2026-09-25", kind: "capsule", href: "/timeline" });
    expect(JSON.stringify(events)).not.toContain("a secret plan");
    expect(buildEvents({ notes: [capsule(["capsule", "capsule-not-a-date"])], today: TODAY })).toEqual([]);
  });

  it("sorts the day's rows in a stable order and groups them by date", () => {
    const events = buildEvents({
      applications: [application()],
      interviews: [interview()],
      followUps: [followUp()],
      notes: [capsule(["capsule", "capsule-2026-09-20"])],
      today: TODAY,
    });
    expect(events.map((event) => event.date)).toEqual([
      "2026-09-10",
      "2026-09-12",
      events.find((event) => event.kind === "capsule")!.date,
      events.find((event) => event.kind === "reminder")!.date,
    ]);
    const september = eventsInMonth(events, "2026-09");
    expect(september.get("2026-09-20")?.map((event) => event.kind)).toEqual(["reminder", "capsule"]);
    expect(eventsInMonth(events, "2026-10").size).toBe(0);
  });

  it("counts each kind and names the next day on or after today", () => {
    const events = buildEvents({
      applications: [application()],
      interviews: [interview()],
      followUps: [followUp()],
      today: TODAY,
    });
    expect(summarize(events)).toEqual({ reminder: 1, interview: 1, followup: 1, capsule: 0 });
    expect(nextEvent(events, TODAY)?.date).toBe("2026-09-20");
    expect(nextEvent(events, "2026-10-01")).toBeNull();
  });
});
