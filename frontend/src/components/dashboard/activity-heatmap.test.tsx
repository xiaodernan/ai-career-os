import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

vi.mock("@/lib/i18n/locale-context", () => ({
  useLocale: () => ({
    locale: "en",
    t: (key: string, vars?: Record<string, unknown>) =>
      vars ? `[${key}|${Object.values(vars).join(",")}]` : `[${key}]`,
    setLocale: () => undefined,
  }),
}));

const state = vi.hoisted(() => ({
  data: null as null | {
    days: number;
    grid: Array<{
      date: string;
      applications: number;
      interviews: number;
      replies: number;
      aiCalls: number;
    }>;
    streak: { current: number; longest: number };
    grandTotal: number;
  },
}));

vi.mock("@/lib/hooks/monitoring", () => ({
  useActivityHeatmap: () =>
    state.data
      ? { data: state.data, isPending: false, isError: false }
      : { data: undefined, isPending: true, isError: false },
}));

import { ActivityHeatmap } from "./activity-heatmap";

function day(date: string, total: number) {
  // Total rides the applications count; the ramp reads the sum only.
  return { date, applications: total, interviews: 0, replies: 0, aiCalls: 0 };
}

describe("ActivityHeatmap", () => {
  it("shows the skeleton while the grid is pending", () => {
    const html = renderToStaticMarkup(<ActivityHeatmap />);
    expect(html).toContain("data-slot=\"skeleton\"");
  });

  it("renders the streaks, the legend and one cell per day — quiet days included", () => {
    // 10 days, the middle three silent: a grid that omitted them would be a shorter
    // calendar, and the silence between two busy stretches is the thing it exists to show.
    state.data = {
      days: 10,
      grid: [
        day("2026-11-02", 2),
        day("2026-11-03", 0),
        day("2026-11-04", 0),
        day("2026-11-05", 0),
        day("2026-11-06", 5),
        day("2026-11-07", 1),
        day("2026-11-08", 0),
        day("2026-11-09", 12),
        day("2026-11-10", 3),
        day("2026-11-11", 0),
      ],
      streak: { current: 2, longest: 3 },
      grandTotal: 23,
    };

    const html = renderToStaticMarkup(<ActivityHeatmap />);

    expect(html).toContain("[dashboard.heatmapTitle]");
    expect(html).toContain("[dashboard.heatmapCurrentStreak]");
    expect(html).toContain("[dashboard.heatmapLongestStreak]");
    expect(html).toContain("[dashboard.heatmapTotal]");
    expect(html).toContain(">23<");
    expect(html).toContain("2026-11-09");
    // The silence is on the grid: an empty day's cell renders with the muted ramp.
    expect(html).toContain("2026-11-03");
  });

  it("tells an all-quiet window the truth instead of drawing an empty grid", () => {
    state.data = {
      days: 10,
      grid: [day("2026-11-02", 0), day("2026-11-03", 0)],
      streak: { current: 0, longest: 0 },
      grandTotal: 0,
    };

    const html = renderToStaticMarkup(<ActivityHeatmap />);
    expect(html).toContain("[dashboard.heatmapEmpty]");
  });

  it("labels a cell with what the day carried, in the reader's language", () => {
    state.data = {
      days: 1,
      grid: [{ date: "2026-11-09", applications: 1, interviews: 2, replies: 0, aiCalls: 4 }],
      streak: { current: 1, longest: 1 },
      grandTotal: 7,
    };

    const html = renderToStaticMarkup(<ActivityHeatmap />);
    expect(html).toContain("2026-11-09");
    expect(html).toContain("[dashboard.applications|1]");
    expect(html).toContain("[dashboard.interviews|2]");
    expect(html).toContain("[dashboard.heatmapAiCalls|4]");
  });
});
