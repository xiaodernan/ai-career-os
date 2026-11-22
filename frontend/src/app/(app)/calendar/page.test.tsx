import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

const state = vi.hoisted(() => ({
  applications: [] as Record<string, unknown>[],
  interviews: [] as Record<string, unknown>[],
  followUps: [] as Record<string, unknown>[],
  notes: [] as Record<string, unknown>[],
  url: { month: "2026-09" } as { month?: string },
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
    expect(html).toContain("4 things on the month");
    // Three chips are drawn; the fourth is named by the counter.
    expect(html).toContain("Role 1");
    expect(html).toContain("Role 2");
    expect(html).toContain("Role 3");
    expect(html).not.toContain("Role 4<");
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
  });
});
