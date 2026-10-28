import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

// The identity translator keeps the card's keys visible in the markup, with the holes
// appended, so an assertion can name the key and the value it got.
vi.mock("@/lib/i18n/locale-context", () => ({
  useLocale: () => ({
    locale: "en",
    t: (key: string, vars?: Record<string, unknown>) =>
      vars ? `${key}|${Object.values(vars).join(",")}` : key,
    setLocale: () => {},
  }),
}));

const state = vi.hoisted(() => ({
  reports: {
    data: undefined as
      | { items: unknown[]; total: number; page: number; size: number }
      | undefined,
    isPending: false,
    isError: false,
    isFetching: false,
    error: undefined as unknown,
    refetch: () => {},
  },
}));

vi.mock("@/lib/hooks/monitoring", () => ({
  useNightlyReports: () => state.reports,
}));

import { NightlyHistory } from "./nightly-history";

/**
 * The nightly history card (roadmap 20.1) keeps the same quiet promises as the other
 * list panels: the empty copy waits for the answer, a failed read is named instead of
 * drawn as an empty history, and a step shows the measurement only when the job wrote one.
 */

const REPORT = {
  id: "report-1",
  source: "nightly",
  status: "passed",
  commitSha: "d8199f8aa11",
  runUrl: "https://github.example/actions/runs/1",
  startedAt: "2026-10-27T03:17:00Z",
  finishedAt: "2026-10-27T03:41:12Z",
  steps: [
    { name: "backend-it", status: "passed", detail: "412 passed, 0 failed" },
    { name: "evals", status: "passed", detail: "recall 0.83" },
    { name: "export", status: "passed", detail: null },
  ],
};

function render(): string {
  return renderToStaticMarkup(<NightlyHistory />);
}

beforeEach(() => {
  state.reports = {
    data: undefined,
    isPending: false,
    isError: false,
    isFetching: false,
    error: undefined,
    refetch: () => {},
  };
});

describe("NightlyHistory", () => {
  it("shows a night with its status, commit, steps and the run it came from", () => {
    state.reports.data = { items: [REPORT], total: 1, page: 0, size: 10 };
    const html = render();
    expect(html).toContain("monitoring.nightlyTitle");
    expect(html).toContain("monitoring.nightlyPassed");
    expect(html).toContain("d8199f8");
    expect(html).toContain("backend-it");
    expect(html).toContain("evals");
    expect(html).toContain('title="recall 0.83"');
    expect(html).toContain("https://github.example/actions/runs/1");
    expect(html).toContain("monitoring.nightlyOpenRun");
    expect(html).not.toContain("monitoring.nightlyEmpty");
  });

  it("names a failed night as failed and keeps the steps it reported", () => {
    state.reports.data = {
      items: [
        {
          ...REPORT,
          id: "report-2",
          status: "failed",
          steps: [
            { name: "backend-it", status: "failed", detail: "410 passed, 2 failed" },
            { name: "evals", status: "skipped", detail: null },
          ],
        },
      ],
      total: 1,
      page: 0,
      size: 10,
    };
    const html = render();
    expect(html).toContain("monitoring.nightlyFailed");
    expect(html).toContain("backend-it");
    expect(html).toContain('title="410 passed, 2 failed"');
  });

  it("holds the empty copy until the history has actually answered", () => {
    state.reports.isPending = true;
    expect(render()).not.toContain("monitoring.nightlyEmpty");

    state.reports.isPending = false;
    state.reports.data = { items: [], total: 0, page: 0, size: 10 };
    expect(render()).toContain("monitoring.nightlyEmpty");
  });

  it("names a failed read rather than pretending the history is empty", () => {
    state.reports.isError = true;
    state.reports.error = new Error("boom");
    const html = render();
    expect(html).toContain("monitoring.nightlyUnavailable");
    expect(html).not.toContain("monitoring.nightlyEmpty");
  });

  it("offers the older nights only when there are more than one page", () => {
    state.reports.data = { items: [REPORT], total: 1, page: 0, size: 10 };
    expect(render()).not.toContain("monitoring.nightlyPagination");

    state.reports.data = { items: [REPORT], total: 11, page: 0, size: 10 };
    expect(render()).toContain("monitoring.nightlyPagination");
  });
});
