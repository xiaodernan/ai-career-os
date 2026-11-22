import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

const state = vi.hoisted(() => ({
  applications: [] as Record<string, unknown>[],
  interviews: [] as Record<string, unknown>[],
  followUps: [] as Record<string, unknown>[],
  notes: [] as Record<string, unknown>[],
  url: { month: "2026-09" } as { month?: string; view?: string; day?: string },
  written: undefined as Record<string, unknown> | undefined,
}));

const quiet = vi.hoisted(() => ({ isPending: false, isError: false, isFetching: false, error: null, refetch: () => {} }));

vi.mock("@/lib/hooks/resources", () => ({
  useApplications: () => ({ data: { items: state.applications, total: state.applications.length }, ...quiet }),
  useInterviewSessions: () => ({ data: { items: state.interviews, total: state.interviews.length }, ...quiet }),
  useDashboard: () => ({ data: { followUps: state.followUps }, ...quiet }),
  useKnowledgeNotes: () => ({ data: { items: state.notes, total: state.notes.length }, ...quiet }),
}));

vi.mock("@/lib/hooks/use-url-state", () => ({
  useUrlState: () => [
    state.url,
    (patch: Record<string, unknown>) => {
      state.written = patch;
    },
  ],
}));

import CalendarPage from "./page";
import { LocaleProvider } from "@/lib/i18n/locale-context";

/**
 * Epic 386 — the calendar page. It draws the month from rows the other screens
 * already hold; this test grades the grid, the links and the honest empty shelf,
 * never a new read.
 */
function render(locale: "en" | "zh" = "en"): string {
  vi.stubGlobal("window", {
    localStorage: { getItem: () => locale, setItem: () => {} },
  });
  return renderToStaticMarkup(
    <LocaleProvider>
      <CalendarPage />
    </LocaleProvider>
  );
}

beforeEach(() => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date(2026, 8, 15, 12, 0, 0));
  state.applications = [];
  state.interviews = [];
  state.followUps = [];
  state.notes = [];
  state.url = { month: "2026-09" };
  state.written = undefined;
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("the calendar page", () => {
  it("draws the month's rows on their own days with their own doors", () => {
    state.applications = [
      { id: "app-1", title: "Backend Engineer", companyName: "Acme Robotics", status: "applied", reminderAt: "2026-09-20T09:00:00Z" },
    ];
    state.interviews = [
      { id: "int-1", mode: "technical", status: "completed", jobTitle: "Staff Engineer", companyName: "Lunar Works", startedAt: "2026-09-10T10:00:00Z" },
    ];
    state.followUps = [{ id: "c-1", name: "Ada Byron", company: "Analytical Engines", daysSince: 10, cadenceDays: 7 }];
    state.notes = [{ id: "n-1", title: "", content: "a secret plan", tags: ["capsule", "capsule-2026-09-25"] }];

    const html = render();

    expect(html).toContain("September 2026");
    expect(html).toContain("Backend Engineer");
    expect(html).toContain('href="/applications?application=app-1"');
    expect(html).toContain("Staff Engineer");
    expect(html).toContain('href="/interviews/int-1"');
    expect(html).toContain("Ada Byron");
    expect(html).toContain("Follow-up due");
    expect(html).toContain("Sealed letter opens");
    expect(html).toContain("A letter to your future self");
    // The sealed body never reaches the month.
    expect(html).not.toContain("a secret plan");
  });

  it("counts the month and says how many rows a day hides", () => {
    state.applications = Array.from({ length: 4 }, (_, index) => ({
      id: `app-${index + 1}`,
      title: `Role ${index + 1}`,
      companyName: "Acme",
      status: "applied",
      reminderAt: "2026-09-20T09:00:00Z",
    }));

    const html = render();

    expect(html).toContain("+1 more");
    // Epic 390 — the counter is a door into that day's complete week column.
    expect(html).toMatch(/<button[^>]*title="See every row on this day, in the week"[^>]*>\+1 more<\/button>/);
    expect(html).toContain("4 things on the month");
    // Three chips are drawn; the fourth is named by the counter.
    expect(html).toContain("Role 1");
    expect(html).toContain("Role 2");
    expect(html).toContain("Role 3");
    expect(html).not.toContain("Reminder · Role 4");
  });

  it("names the next five rows as a runway, with the wait beside each", () => {
    state.applications = Array.from({ length: 6 }, (_, index) => ({
      id: `app-${index + 1}`,
      title: `Later ${index + 1}`,
      companyName: "Acme",
      status: "applied",
      reminderAt: `2026-10-${String(index + 1).padStart(2, "0")}T12:00:00Z`,
    }));

    const html = render();

    // October rows are not on the September grid, yet the runway still names them.
    expect(html).toContain("Next up");
    for (let index = 1; index <= 5; index += 1) expect(html).toContain(`Later ${index}`);
    expect(html).not.toContain("Later 6");
    expect(html).toContain("In 16 days");
    expect(html).toContain('href="/applications?application=app-5"');
    expect(html).not.toContain('href="/applications?application=app-6"');
  });

  it("keeps the grid honest when the month holds nothing", () => {
    const html = render();
    expect(html).toContain("Nothing lands on this month yet");
    expect(html).toContain("The calendar is still blank");
    expect(html).toContain('href="/applications"');
    expect(html).toContain('href="/timeline"');
    expect(html).toContain('href="/networking"');
  });

  it("speaks Chinese to a Chinese reader, controls and all", () => {
    const html = render("zh");
    expect(html).toContain("2026年9月");
    expect(html).toContain("上个月");
    expect(html).toContain("下个月");
    expect(html).toContain("回到本月");
    expect(html).toContain("该跟进了");
  });

  it("offers one control per way of walking the calendar", () => {
    const html = render();
    expect(html).toContain('aria-label="Previous month"');
    expect(html).toContain('aria-label="Next month"');
    expect(html).toContain("Today");
    // Both layouts are named up front, with the month standing.
    expect(html).toContain('aria-label="How the calendar is laid out"');
    expect(html).toContain(">Month<");
    expect(html).toContain(">Week<");
    expect(html).toContain('aria-pressed="true"');
    // Epic 391 — the days on screen can leave as a calendar file.
    expect(html).toContain("Export calendar");
    // Epic 394 — the keyboard is named where the legend lives.
    expect(html).toContain("Keyboard: ← → walk one month or week, T returns to today.");
  });

  it("opens a week with every row of each day, detail and all", () => {
    state.url = { view: "week", day: "2026-09-16" };
    state.applications = Array.from({ length: 5 }, (_, index) => ({
      id: `app-${index + 1}`,
      title: `Role ${index + 1}`,
      companyName: "Acme Robotics",
      status: "applied",
      reminderAt: "2026-09-16T09:00:00Z",
    }));

    const html = render();

    expect(html).toContain("Sep 14 – Sep 20, 2026");
    expect(html).toContain("5 things this week");
    // Epic 395 — the week reads its own rhythm: five rows on one Wednesday.
    expect(html).toContain(
      "This week — rows: 5 · active days: 1 · busiest: Wednesday (5) · open days: 6"
    );
    // The week has room for the whole day: no chip is folded behind a counter.
    for (let index = 1; index <= 5; index += 1) expect(html).toContain(`Role ${index}`);
    expect(html).not.toContain("more</button>");
    expect(html).toContain("Acme Robotics");
    expect(html).toContain('href="/applications?application=app-1"');
    expect(html).toContain('aria-label="Previous week"');
    expect(html).toContain('aria-label="Next week"');
    // Days with nothing still hold their column.
    expect(html.match(/—/g)?.length ?? 0).toBeGreaterThanOrEqual(6);
  });

  it("keeps the week honest when the seven days hold nothing", () => {
    state.url = { view: "week", day: "2026-09-16" };
    const html = render();
    expect(html).toContain("Sep 14 – Sep 20, 2026");
    expect(html).toContain("0 things this week");
    expect(html).toContain("Nothing lands on this week yet");
    // Nothing to carry: the export stays disabled rather than writing an empty file.
    expect(html).toMatch(/<button[^>]*disabled[^>]*>[\s\S]*?Export calendar<\/button>/);
  });

  it("speaks a week in Chinese, controls and all", () => {
    state.url = { view: "week", day: "2026-09-16" };
    const html = render("zh");
    expect(html).toContain("2026年9月14日 – 9月20日");
    expect(html).toContain("按周");
    expect(html).toContain("上一周");
    expect(html).toContain("下一周");
    expect(html).toContain("本周有 0 件事");
  });

  it("names the busiest day in Chinese", () => {
    state.url = { view: "week", day: "2026-09-16" };
    state.applications = [
      {
        id: "app-1",
        title: "后端工程师",
        companyName: "Acme",
        status: "applied",
        reminderAt: "2026-09-16T09:00:00Z",
      },
    ];
    const html = render("zh");
    expect(html).toContain("本周——共 1 件 · 有事 1 天 · 最满 星期三（1 件）· 空着 6 天");
  });
});
