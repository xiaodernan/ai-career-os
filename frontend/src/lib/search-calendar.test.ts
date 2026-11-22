import { describe, expect, it } from "vitest";

import {
  buildEvents,
  dateKeyOf,
  daysPast,
  eventsInMonth,
  eventsInWeek,
  followUpDue,
  isOverdue,
  monthCells,
  monthKeyOf,
  nextEvent,
  overdueEvents,
  readCalendarView,
  readDayKey,
  readMonthKey,
  searchEvents,
  shiftDays,
  shiftMonth,
  summarize,
  upcomingEvents,
  weekCells,
  weekTempo,
  type CalendarEvent,
} from "@/lib/search-calendar";
import type { Application, FollowUpItem, InterviewSession, KnowledgeNote, OfferShelfItem } from "@/lib/api/types";

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

function offer(overrides: Partial<OfferShelfItem> = {}): OfferShelfItem {
  return {
    id: "offer-1",
    label: "Lunar Works · Staff Engineer",
    base: 180000,
    bonus: 20000,
    equity: 40000,
    currency: "USD",
    remoteType: "hybrid",
    deadline: "2026-09-24T12:00:00Z",
    notes: null,
    totalComp: 240000,
    createdAt: "2026-09-01T00:00:00Z",
    updatedAt: "2026-09-01T00:00:00Z",
    decision: "pending",
    ...overrides,
  };
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

  it("puts a pending offer deadline on its day and drops a decided one", () => {
    const events = buildEvents({
      offers: [
        offer(),
        offer({ id: "offer-2", decision: "accepted" }),
        offer({ id: "offer-3", decision: "declined" }),
        offer({ id: "offer-4", deadline: null }),
      ],
      today: TODAY,
    });
    expect(events).toHaveLength(1);
    expect(events[0]).toMatchObject({
      id: "offer-offer-1",
      kind: "offer",
      title: "Lunar Works · Staff Engineer",
      href: "/offers",
    });
    expect(events[0].date).toMatch(/^2026-09-(24|25)$/);
    // An offer without a decision is still pending, not silently dropped.
    expect(buildEvents({ offers: [offer({ decision: undefined })], today: TODAY })).toHaveLength(1);
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
    expect(summarize(events)).toEqual({ reminder: 1, interview: 1, followup: 1, offer: 0, capsule: 0 });
    expect(nextEvent(events, TODAY)?.date).toBe("2026-09-20");
    expect(nextEvent(events, "2026-10-01")).toBeNull();
  });
});

describe("the week around a day", () => {
  it("reads a real day and refuses an impossible one", () => {
    expect(readDayKey("2026-09-15")).toBe("2026-09-15");
    expect(readDayKey("2026-02-30")).toBeNull();
    expect(readDayKey("2026-9-15")).toBeNull();
    expect(readDayKey(undefined)).toBeNull();
  });

  it("steps seven days at a time across months, years and leap days", () => {
    expect(shiftDays("2026-09-28", 7)).toBe("2026-10-05");
    expect(shiftDays("2026-01-02", -7)).toBe("2025-12-26");
    expect(shiftDays("2024-02-28", 1)).toBe("2024-02-29");
    expect(shiftDays("2024-12-31", 1)).toBe("2025-01-01");
  });

  it("draws Monday through Sunday around any day, dimming the month's strangers", () => {
    expect(weekCells("2026-09-16").map((cell) => cell.date)).toEqual([
      "2026-09-14",
      "2026-09-15",
      "2026-09-16",
      "2026-09-17",
      "2026-09-18",
      "2026-09-19",
      "2026-09-20",
    ]);
    expect(weekCells("2026-09-16").every((cell) => cell.inMonth)).toBe(true);

    const straddling = weekCells("2026-10-01");
    expect(straddling[0].date).toBe("2026-09-28");
    expect(straddling[0].inMonth).toBe(false);
    expect(straddling[3].date).toBe("2026-10-01");
    expect(straddling[3].inMonth).toBe(true);
  });

  it("only switches to the week on the exact word", () => {
    expect(readCalendarView("week")).toBe("week");
    expect(readCalendarView("Week")).toBe("month");
    expect(readCalendarView("month")).toBe("month");
    expect(readCalendarView(undefined)).toBe("month");
  });

  it("groups the seven days' rows and leaves the weeks either side out", () => {
    const events = buildEvents({
      applications: [
        application({ id: "a-in", reminderAt: "2026-09-16T09:00:00Z" }),
        application({ id: "a-before", reminderAt: "2026-09-13T09:00:00Z" }),
        application({ id: "a-after", reminderAt: "2026-09-21T09:00:00Z" }),
      ],
      today: TODAY,
    });
    const week = eventsInWeek(events, "2026-09-16");
    expect([...week.values()].flat().map((event) => event.id)).toEqual(["reminder-a-in"]);
    expect([...week.keys()].every((date) => date >= "2026-09-14" && date <= "2026-09-20")).toBe(true);
  });

  it("still counts and names the next row from the whole list", () => {
    const events = buildEvents({ applications: [application()], today: TODAY });
    const week = eventsInWeek(events, "2026-09-10");
    expect(summarize([...week.values()].flat())).toEqual({
      reminder: 0,
      interview: 0,
      followup: 0,
      offer: 0,
      capsule: 0,
    });
    expect(nextEvent(events, "2026-09-10")?.id).toBe("reminder-app-1");
  });
});

describe("the runway ahead", () => {
  const rows: CalendarEvent[] = Array.from({ length: 7 }, (_, index) => ({
    id: `e-${index}`,
    date: `2026-09-${String(14 + index).padStart(2, "0")}`,
    kind: "reminder",
    title: `Row ${index}`,
  }));

  it("starts on today, never in the past, and takes only what was asked", () => {
    const runway = upcomingEvents(rows, "2026-09-15", 5);
    expect(runway.map((event) => event.date)).toEqual([
      "2026-09-15",
      "2026-09-16",
      "2026-09-17",
      "2026-09-18",
      "2026-09-19",
    ]);
    expect(upcomingEvents(rows, "2026-09-15", 0)).toEqual([]);
    expect(upcomingEvents(rows, "2026-09-15", -3)).toEqual([]);
    expect(upcomingEvents(rows, "2026-10-01")).toEqual([]);
  });

  it("keeps the first row of the runway identical to the old next-up", () => {
    expect(nextEvent(rows, "2026-09-15")?.id).toBe(upcomingEvents(rows, "2026-09-15", 5)[0].id);
  });
});

describe("the month under load", () => {
  it("holds twenty thousand dated rows and still answers a month and a week", () => {
    // A flood of rows is what a long search looks like. Nothing here should
    // degrade to a nested scan: the same pure fold that serves four rows serves
    // twenty thousand, and the counts stay honest.
    const applications = Array.from({ length: 20_000 }, (_, index) =>
      application({
        id: `flood-${index}`,
        reminderAt: `2026-09-${String((index % 28) + 1).padStart(2, "0")}T12:00:00Z`,
      })
    );
    const events = buildEvents({ applications, today: TODAY });
    expect(events).toHaveLength(20_000);
    expect(summarize(events).reminder).toBe(20_000);
    expect([...eventsInMonth(events, "2026-09").values()].flat()).toHaveLength(20_000);
    const week = [...eventsInWeek(events, "2026-09-16").values()].flat();
    expect(week.length).toBeGreaterThan(0);
    expect(week.every((event) => event.date >= "2026-09-14" && event.date <= "2026-09-20")).toBe(true);
    expect(upcomingEvents(events, TODAY, 5)).toHaveLength(5);
  });
});

describe("the week's rhythm", () => {
  const cells = weekCells("2026-09-16");
  const row = (date: string, id: string): CalendarEvent => ({
    id,
    date,
    kind: "reminder",
    title: id,
  });

  it("counts rows, days that carry one, and days that stay open", () => {
    const events = new Map<string, CalendarEvent[]>([
      ["2026-09-14", [row("2026-09-14", "a")]],
      ["2026-09-15", [row("2026-09-15", "b"), row("2026-09-15", "c")]],
      ["2026-09-16", [row("2026-09-16", "d")]],
    ]);
    expect(weekTempo(cells, events)).toEqual({
      total: 4,
      activeDays: 3,
      openDays: 4,
      busiest: { date: "2026-09-15", count: 2 },
    });
  });

  it("gives a tie to the earlier day and calls a quiet week empty", () => {
    const events = new Map<string, CalendarEvent[]>([
      ["2026-09-18", [row("2026-09-18", "a")]],
      ["2026-09-15", [row("2026-09-15", "b")]],
    ]);
    expect(weekTempo(cells, events).busiest).toEqual({ date: "2026-09-15", count: 1 });
    expect(weekTempo(cells, new Map())).toEqual({
      total: 0,
      activeDays: 0,
      openDays: 7,
      busiest: null,
    });
  });
});

/**
 * Epic 405 — the runway keeps only rows on or after today, so a follow-up that
 * went due last week used to fall off the one card a reader checks in the
 * morning. These cases pin what "late" means: only the three kinds that ask for
 * an answer, only strictly before today, and the oldest row first.
 */
describe("the rows the runway cannot hold", () => {
  const row = (date: string, kind: CalendarEvent["kind"]): CalendarEvent => ({
    id: `${kind}-${date}`,
    date,
    kind,
    title: `${kind} on ${date}`,
  });

  it("counts a reminder, a follow-up and an offer as late once their day passes", () => {
    expect(isOverdue(row("2026-09-14", "reminder"), TODAY)).toBe(true);
    expect(isOverdue(row("2026-09-14", "followup"), TODAY)).toBe(true);
    expect(isOverdue(row("2026-09-14", "offer"), TODAY)).toBe(true);
  });

  it("leaves today alone and keeps a rehearsal or an opened letter as history", () => {
    expect(isOverdue(row("2026-09-15", "reminder"), TODAY)).toBe(false);
    expect(isOverdue(row("2026-09-16", "offer"), TODAY)).toBe(false);
    expect(isOverdue(row("2026-09-14", "interview"), TODAY)).toBe(false);
    expect(isOverdue(row("2026-09-14", "capsule"), TODAY)).toBe(false);
  });

  it("puts the row that has waited longest first, and caps the list but not the count", () => {
    const events = [
      row("2026-09-10", "followup"),
      row("2026-09-12", "reminder"),
      row("2026-09-08", "offer"),
      row("2026-09-14", "capsule"),
      row("2026-09-13", "interview"),
    ];
    const slice = overdueEvents(events, TODAY, 2);
    expect(slice.items.map((event) => event.id)).toEqual(["offer-2026-09-08", "followup-2026-09-10"]);
    expect(slice.total).toBe(3);
    expect(overdueEvents(events, TODAY, 0)).toEqual({ items: [], total: 3 });
  });

  it("does not reorder the caller's array", () => {
    const events = [row("2026-09-10", "followup"), row("2026-09-08", "offer")];
    overdueEvents(events, TODAY, 5);
    expect(events.map((event) => event.date)).toEqual(["2026-09-10", "2026-09-08"]);
  });

  it("finds a follow-up that went due and an offer still pending in the rows themselves", () => {
    const events = buildEvents({
      followUps: [followUp({ daysSince: 12, cadenceDays: 7 })],
      offers: [
        offer({ id: "o-pending", deadline: "2026-09-12T00:00:00Z", decision: "pending" }),
        offer({ id: "o-taken", deadline: "2026-09-12T00:00:00Z", decision: "accepted" }),
      ],
      today: TODAY,
    });
    const slice = overdueEvents(events, TODAY, 5);
    expect(slice.total).toBe(2);
    expect(slice.items.map((event) => event.kind)).toEqual(["followup", "offer"]);
    expect(slice.items.every((event) => event.date < TODAY)).toBe(true);
  });

  it("measures lateness in whole local days and never counts forward", () => {
    expect(daysPast("2026-09-14", TODAY)).toBe(1);
    expect(daysPast("2026-09-01", TODAY)).toBe(14);
    expect(daysPast("2026-09-15", TODAY)).toBe(0);
    expect(daysPast("2026-09-16", TODAY)).toBe(0);
    expect(daysPast("not a date", TODAY)).toBe(0);
  });
});

/**
 * Epic 408 — a long calendar needs to be searchable. The query is the reader's
 * own words against the row's own words; these cases pin the folding, the
 * newest-first order, and the rule that an empty box finds nothing.
 */
describe("finding a row on a long calendar", () => {
  const row = (date: string, title: string, detail?: string): CalendarEvent => ({
    id: `${title}-${date}`,
    date,
    kind: "reminder",
    title,
    detail,
  });

  it("finds a role or a company by a fragment, ignoring case and the ends", () => {
    const events = [
      row("2026-09-10", "Backend Engineer", "Acme Robotics"),
      row("2026-09-11", "Designer", "Lunar Works"),
    ];
    expect(searchEvents(events, "  acme ").items.map((event) => event.id)).toEqual([
      "Backend Engineer-2026-09-10",
    ]);
    expect(searchEvents(events, "ENGINEER").total).toBe(1);
    expect(searchEvents(events, "works").items[0].id).toBe("Designer-2026-09-11");
  });

  it("returns the newest match first and caps the list without capping the count", () => {
    const events = [row("2026-09-10", "Acme"), row("2026-09-20", "Acme"), row("2026-09-15", "Acme")];
    const slice = searchEvents(events, "acme", 2);
    expect(slice.items.map((event) => event.date)).toEqual(["2026-09-20", "2026-09-15"]);
    expect(slice.total).toBe(3);
    expect(searchEvents(events, "acme", 0)).toEqual({ items: [], total: 3 });
  });

  it("finds nothing for an empty or blank query", () => {
    const events = [row("2026-09-10", "Acme")];
    expect(searchEvents(events, "")).toEqual({ items: [], total: 0 });
    expect(searchEvents(events, "   ")).toEqual({ items: [], total: 0 });
  });

  it("does not reorder the caller's array", () => {
    const events = [row("2026-09-10", "Acme"), row("2026-09-20", "Acme")];
    searchEvents(events, "acme", 5);
    expect(events.map((event) => event.date)).toEqual(["2026-09-10", "2026-09-20"]);
  });
});
