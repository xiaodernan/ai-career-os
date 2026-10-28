import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

// The identity translator keeps the panel's keys visible in the markup, with
// the holes appended, so an assertion can name the key and the value it got.
vi.mock("@/lib/i18n/locale-context", () => ({
  useLocale: () => ({
    locale: "en",
    t: (key: string, vars?: Record<string, unknown>) =>
      vars ? `${key}|${Object.values(vars).join(",")}` : key,
    setLocale: () => {},
  }),
}));

const state = vi.hoisted(() => ({
  feeds: { data: undefined as unknown[] | undefined, isSuccess: false, isError: false },
  runs: { data: undefined as unknown[] | undefined, isSuccess: false, isError: false },
  detail: {
    data: undefined as { run: unknown; plan: unknown } | undefined,
    isPending: false,
  },
}));

vi.mock("@/lib/hooks/resources", () => ({
  useIngestionFeeds: () => state.feeds,
  useIngestionRuns: () => state.runs,
  useIngestionRunDetail: () => state.detail,
}));

vi.mock("@/lib/hooks/ingestion", () => ({
  useCreateIngestionFeed: () => ({ mutate: () => {}, isPending: false }),
  useToggleIngestionFeed: () => ({ mutate: () => {}, isPending: false }),
  useDeleteIngestionFeed: () => ({ mutate: () => {}, isPending: false }),
  useRunIngestionFeed: () => ({ mutate: () => {}, isPending: false, variables: undefined }),
}));

import { ScheduledFeedsPanel, planTitles } from "./scheduled-feeds-panel";

/**
 * The scheduled-feeds panel is the browser's half of the nightly sweep
 * (19.2). Its two quiet promises are the same kind the saved-search panel
 * keeps: the empty copy speaks only once the list has answered, and a failed
 * pull is shown as the run it is — with the reason the server wrote down —
 * rather than as an error state the reader cannot act on.
 */

const FEED = {
  id: "feed-1",
  name: "HN hiring",
  url: "https://hn.example/rss",
  source: "rss",
  enabled: true,
  lastRun: {
    id: "run-1",
    feedId: "feed-1",
    feedName: "HN hiring",
    status: "completed",
    counts: { incoming: 5, create: 3, update: 2, close: 1, duplicates: 1 },
    startedAt: "2026-10-27T03:20:00Z",
  },
};

function render(): string {
  return renderToStaticMarkup(<ScheduledFeedsPanel />);
}

beforeEach(() => {
  state.feeds = { data: undefined, isSuccess: false, isError: false };
  state.runs = { data: undefined, isSuccess: false, isError: false };
  state.detail = { data: undefined, isPending: false };
});

describe("planTitles", () => {
  it("reads the titles a stored plan proposes, and nothing else", () => {
    expect(
      planTitles({
        create: [
          { title: "Backend engineer" },
          { title: "  " },
          { title: 42 },
          null,
          { notATitle: true },
        ],
        close: [{ title: "Ignored" }],
      })
    ).toEqual(["Backend engineer"]);
    expect(planTitles(null)).toEqual([]);
    expect(planTitles({ create: "not a list" })).toEqual([]);
  });
});

describe("ScheduledFeedsPanel", () => {
  it("lists a feed with its switch, its last run and its counts", () => {
    state.feeds = { data: [FEED], isSuccess: true, isError: false };
    state.runs = { data: [FEED.lastRun], isSuccess: true, isError: false };
    const html = render();
    expect(html).toContain("HN hiring");
    expect(html).toContain("https://hn.example/rss");
    expect(html).toContain("ingestion.toggleAria|HN hiring");
    expect(html).toContain("ingestion.deleteFeedAria|HN hiring");
    expect(html).toContain("ingestion.lastRun");
    expect(html).toContain("ingestion.statusCompleted");
    expect(html).toContain("ingestion.incomingBadge|5");
    expect(html).toContain("ingestion.createBadge|3");
    expect(html).toContain("ingestion.updateBadge|2");
    expect(html).toContain("ingestion.duplicateBadge|1");
    expect(html).toContain("ingestion.closeBadge|1");
    expect(html).toContain("ingestion.viewPlan");
    expect(html).not.toContain("ingestion.noFeeds");
    expect(html).not.toContain("ingestion.noRuns");
  });

  it("says a feed was never run instead of leaving the line blank", () => {
    state.feeds = {
      data: [{ id: "feed-2", name: "New", url: "https://x.example/rss", source: "feed", enabled: false, lastRun: null }],
      isSuccess: true,
      isError: false,
    };
    state.runs = { data: [], isSuccess: true, isError: false };
    const html = render();
    expect(html).toContain("ingestion.neverRun");
    expect(html).toContain("ingestion.noRuns");
  });

  it("shows a failed pull as the run it is, with the server's reason", () => {
    const failed = {
      id: "run-2",
      feedId: "feed-1",
      feedName: "HN hiring",
      status: "failed",
      error: "Feed answered HTTP 503",
      startedAt: "2026-10-27T03:20:00Z",
    };
    state.feeds = { data: [FEED], isSuccess: true, isError: false };
    state.runs = { data: [failed], isSuccess: true, isError: false };
    const html = render();
    expect(html).toContain("ingestion.statusFailed");
    expect(html).toContain("Feed answered HTTP 503");
    // A failed run recorded no plan, so there is nothing to open.
    expect(html).not.toContain("ingestion.viewPlan");
  });

  it("holds the empty copy until each list has actually answered", () => {
    const pending = render();
    expect(pending).not.toContain("ingestion.noFeeds");
    expect(pending).not.toContain("ingestion.noRuns");

    state.feeds = { data: [], isSuccess: true, isError: false };
    state.runs = { data: [], isSuccess: true, isError: false };
    const empty = render();
    expect(empty).toContain("ingestion.noFeeds");
    expect(empty).toContain("ingestion.noRuns");
  });

  it("names a failed read rather than pretending the lists are empty", () => {
    state.feeds = { data: undefined, isSuccess: false, isError: true };
    state.runs = { data: undefined, isSuccess: false, isError: true };
    const html = render();
    expect(html).toContain("ingestion.feedsUnavailable");
    expect(html).toContain("ingestion.runsUnavailable");
    expect(html).not.toContain("ingestion.noFeeds");
    expect(html).not.toContain("ingestion.noRuns");
  });
});
