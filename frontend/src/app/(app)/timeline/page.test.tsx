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
  url: { kind: undefined as string | undefined },
  written: undefined as Record<string, unknown> | undefined,
}));

vi.mock("@/lib/hooks/timeline", () => ({
  useTimeline: () => state.timeline,
}));

vi.mock("@/lib/hooks/use-url-state", () => ({
  useUrlState: () => [
    state.url,
    (patch: Record<string, unknown>) => {
      state.written = patch;
    },
  ],
}));

import TimelinePage from "./page";
import { LocaleProvider } from "@/lib/i18n/locale-context";

/**
 * The timeline answers "what has my search written down, in order" (Epic 81), extended by
 * 83 (rows link to their screens) and 84 (`?kind=` narrows the fold). This page's own
 * contract is that every kind the engine can emit renders as a named row, a kind nobody
 * knows arrives unnamed rather than silent, the chips narrow to one kind and put `kind`
 * into the URL (and `All kinds` takes it back out), and a narrowing that names a kind
 * nothing produced renders its own honest sentence instead of the generic empty state.
 */

const ROWS: TimelineEntry[] = [
  { at: "2026-09-01T09:00:00Z", kind: "application", title: "Backend Engineer · Acme Robotics", refId: "a-1", summary: "status: applied" },
  { at: "2026-09-02T07:30:00Z", kind: "contact", title: "Added Ada Byron", refId: "c-1", summary: "referrer" },
  { at: "2026-09-03T06:00:00Z", kind: "interview", title: "Backend Engineer", refId: "i-1", summary: "mode mixed, active" },
  { at: "2026-09-04T05:00:00Z", kind: "resume_version", title: "Resume version · tailored-for-mid", refId: "rv-1", summary: "kind: tailored" },
  { at: "2026-09-04T05:00:00Z", kind: "note", title: "Interview prep", refId: "n-1", summary: "#interview" },
  { at: "2026-09-05T00:30:00Z", kind: "match", title: "Match", refId: "m-1", summary: "overall 82.5" },
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
  state.url = { kind: undefined };
  state.written = undefined;
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

  it("renders rows that link to their screens and leaves text-only rows alone", () => {
    state.timeline = {
      data: ROWS,
      isPending: false,
      isError: false,
      isFetching: false,
      error: null,
      refetch: () => {},
    };

    const html = render();

    expect(html).toContain('href="/applications?application=a-1"');
    expect(html).toContain('href="/interviews/i-1"');
    expect(html).toContain('href="/resumes/rv-1"');
    expect(html).not.toContain('href="/contacts/c-1"');
    expect(html).not.toContain('href="/notes/n-1"');
  });

  it("offers one chip per kind in the engine with a count, All kinds first", () => {
    state.timeline = {
      data: ROWS,
      isPending: false,
      isError: false,
      isFetching: false,
      error: null,
      refetch: () => {},
    };

    const html = render();

    expect(html).toContain('aria-label="Narrow the timeline by kind"');
    expect(html).toContain("All kinds");
    expect(html).toContain("Application");
    expect(html).toContain("Note");
    expect(html).toContain(">1<");
    // aria-pressed reflects that nothing is narrowed yet
    expect(html).toContain('aria-pressed="false"');
  });

  it("narrows to the chosen kind and turns the URL back with All kinds", () => {
    state.url = { kind: "note" };
    state.timeline = {
      data: ROWS,
      isPending: false,
      isError: false,
      isFetching: false,
      error: null,
      refetch: () => {},
    };

    const html = render();

    // Only the note row renders under the narrowing
    expect(html).toContain("Interview prep");
    expect(html).not.toContain("Backend Engineer · Acme Robotics");
    expect(html).toContain('aria-pressed="true"');
    expect(html).toContain("All kinds");
  });

  it("renders its own honest empty sentence under a narrowed kind absent from the fold", () => {
    // An absent kind narrows honestly to its own empty sentence instead of the workspace's
    // default empty or a wrong screen.
    state.url = { kind: "education" };
    state.timeline = {
      data: ROWS,
      isPending: false,
      isError: false,
      isFetching: false,
      error: null,
      refetch: () => {},
    };

    const html = render();

    // Zero matches in the fold: the empty state under the narrowing says so.
    expect(html).toContain("rows yet for this account");
    expect(html).not.toContain("Nothing written down yet");
  });

  it("an unknown kind name renders the same honest empty, not a crash", () => {
    state.url = { kind: "bogus-kind" };
    state.timeline = {
      data: ROWS,
      isPending: false,
      isError: false,
      isFetching: false,
      error: null,
      refetch: () => {},
    };

    const html = render();

    expect(html).toContain("rows yet for this account");
  });
});
