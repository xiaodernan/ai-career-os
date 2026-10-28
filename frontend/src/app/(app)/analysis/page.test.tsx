import { describe, expect, it, vi } from "vitest";
import * as React from "react";
import { renderToStaticMarkup } from "react-dom/server";

/**
 * The data is stubbed at the hooks: this test grades the words the page prints
 * around the numbers, not the fetching underneath them.
 */
vi.mock("@/lib/hooks/analytics", () => ({
  useInsightDigest: () => ({
    data: {
      totalApplications: 4,
      activePipeline: 3,
      responseRate: 0.5,
      stalledCount: 1,
      windowDays: 14,
      stageCounts: { oa: 2, final_round: 1 },
      stalled: [
        {
          id: "s1",
          title: "Backend engineer",
          company: "Acme",
          status: "saved",
          daysSinceLastActivity: 3,
        },
      ],
      signals: [],
    },
    isPending: false,
    isError: false,
    isFetching: false,
    refetch: () => {},
  }),
  usePipelineFunnel: () => ({
    data: {
      pipeline: [
        { stage: "oa", count: 2, conversionFromApplied: 0.5 },
        { stage: "final_round", count: 1, conversionFromApplied: 0.25 },
      ],
    },
    isPending: false,
  }),
  useResponseRate: () => ({
    data: {
      responseRate: 0.5,
      interviewRate: 0.25,
      offerRate: 0.25,
      appliedCount: 4,
      respondedCount: 2,
    },
  }),
  useWeeklyDigests: () => ({
    data: [
      {
        id: "w1",
        weekStart: "2026-10-26",
        windowDays: 7,
        generatedAt: "2026-10-27T08:00:00Z",
        payload: {
          totalApplications: 4,
          stalledCount: 1,
          responseRate: 0.5,
          offerRate: 0.25,
          stalled: [
            {
              id: "s1",
              title: "Backend engineer",
              company: "Acme",
              daysSinceLastActivity: 9,
            },
          ],
        },
      },
      {
        id: "w2",
        weekStart: "2026-10-19",
        windowDays: 7,
        generatedAt: "2026-10-20T08:00:00Z",
        payload: { totalApplications: 2, stalledCount: 0 },
      },
    ],
    isPending: false,
    isError: false,
  }),
  useComposeWeeklyDigest: () => ({ mutate: () => {}, isPending: false }),
}));

import AnalysisPage from "./page";
import { LocaleProvider } from "@/lib/i18n/locale-context";

/**
 * The language a render happens in.
 *
 * The provider reads `window.localStorage` on its first render, and node has no
 * window -- so the reader is pinned here rather than assumed.
 */
function render(locale: "en" | "zh"): string {
  vi.stubGlobal("window", {
    localStorage: { getItem: () => locale, setItem: () => {} },
  });
  try {
    return renderToStaticMarkup(
      <LocaleProvider>
        <AnalysisPage />
      </LocaleProvider>
    );
  } finally {
    vi.unstubAllGlobals();
  }
}

/**
 * The page around the numbers.
 *
 * The digest's own sentences arrive from the engine in the reader's language
 * (15.3), and the panel titles come from the table -- but the chart rows and
 * the stalled list are the page's own words, and they were written in English:
 * a stage was spelled with its wire enum, and the funnel's share tail said
 * "of applied" on every screen. A Chinese reader saw English in a page whose
 * every label was Chinese.
 */
describe("the analysis page speaks the reader's language", () => {
  it("names each stage through the table, not its wire enum", () => {
    const zh = render("zh");
    // These three names appear nowhere else on the page -- the rate cells say
    // 回复 / 面试 / 录用 -- so each assertion binds the site it names.
    expect(zh).toContain("在线测评");
    expect(zh).toContain("终面");
    expect(zh).not.toContain("final round");
    // The stalled list's status is a stage too, and this one is its alone.
    expect(zh).toContain("已收藏");
    expect(zh).not.toContain("· saved");
  });

  it("words the funnel's share in the table's language", () => {
    const zh = render("zh");
    expect(zh).toContain("占已投递比例");
    expect(zh).not.toContain("of applied");

    const en = render("en");
    expect(en).toContain("of applied");
    expect(en).toContain("Final round");
    expect(en).toContain("· Saved");
    expect(en).not.toContain("占已投递比例");
  });
});

/**
 * The kept letters (19.4), drawn beside the live digest. The week is a calendar date:
 * formatting it through a timezone would print the Sunday before for some readers, so the
 * assertion is on the date the backend sent, not on a locally shifted one.
 */
describe("the weekly letter", () => {
  it("names the week as a date and counts it", () => {
    const en = render("en");
    expect(en).toContain("Week of Oct 26, 2026");
    expect(en).toContain("9d quiet");
    expect(en).toContain("Earlier letters");
    expect(en).toContain("Compose this week");
  });

  it("speaks the reader's language", () => {
    const zh = render("zh");
    expect(zh).toContain("每周来信");
    expect(zh).toContain("2026年10月26日 当周");
    expect(zh).toContain("已 9 天");
    expect(zh).toContain("更早的来信");
    expect(zh).toContain("生成本周");
    expect(zh).not.toContain("Week of");
  });
});
