import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import type { TimelineEntry } from "@/lib/api/types";

const state = vi.hoisted(() => ({
  timeline: {
    data: undefined as TimelineEntry[] | undefined,
    isPending: false,
    isError: false,
    isFetching: false,
    error: null as unknown,
    refetch: () => {},
  },
}));

vi.mock("@/lib/hooks/timeline", () => ({
  useTimeline: () => state.timeline,
}));

import TimelinePage from "./page";
import { LocaleProvider } from "@/lib/i18n/locale-context";

/**
 * The timeline answers "what has my search written down, in order" (Epic 81). The rows
 * arrive merged by the engine; this page's own contract is that every kind the engine
 * can emit renders as a named row, and a kind nobody knows arrives unnamed rather than
 * silent — a fact that crashed the page would be a fact the reader never sees.
 */

const ROWS: TimelineEntry[] = [
  { at: "2026-09-01T09:00:00Z", kind: "application", title: "Backend Engineer · Acme Robotics", refId: "a-1", summary: "status: applied" },
  { at: "2026-09-02T07:30:00Z", kind: "contact", title: "Added Ada Byron", refId: "c-1", summary: "referrer" },
  { at: "2026-09-03T06:00:00Z", kind: "interview", title: "Backend Engineer", refId: "i-1", summary: "mode mixed, active" },
  { at: "2026-09-04T05:00:00Z", kind: "match", title: "Match", refId: "m-1", summary: "overall 82.5" },
  { at: "2026-09-05T00:00:00Z", kind: "something-else", title: "A kind this page has never heard of", refId: "x-1", summary: "still a fact" },
];

beforeEach(() => {
  state.timeline = {
    data: undefined,
    isPending: false,
    isError: false,
    isFetching: false,
    error: null,
    refetch: () => {},
  };
});

function render(locale: "en" | "zh" = "en"): string {
  vi.stubGlobal("window", {
    localStorage: { getItem: () => locale, setItem: () => {} },
  });
  try {
    return renderToStaticMarkup(
      <LocaleProvider>
        <TimelinePage />
      </LocaleProvider>
    );
  } finally {
    vi.unstubAllGlobals();
  }
}

describe("the timeline", () => {
  it("renders the engine's ordered read with each kind named", () => {
    state.timeline = {
      data: ROWS,
      isPending: false,
      isError: false,
      isFetching: false,
      error: null,
      refetch: () => {},
    };

    const html = render();

    expect(html).not.toContain("timeline.kinds");
    expect(html).toContain("Backend Engineer · Acme Robotics");
    expect(html).toContain("Added Ada Byron");
    expect(html).toContain("referrer");
    expect(html).toContain("Match");
    expect(html).toContain("status: applied");
    // The kind the page does not know still renders, unnamed as itself.
    expect(html).toContain("A kind this page has never heard of");
    expect(html).toContain("Something else");
  });

  it("renders the honest empty state when the loop has written nothing", () => {
    state.timeline = {
      data: [],
      isPending: false,
      isError: false,
      isFetching: false,
      error: null,
      refetch: () => {},
    };

    const html = render();

    expect(html).toContain("Nothing written down yet");
    expect(html).toContain("feeds this list");
  });
});
