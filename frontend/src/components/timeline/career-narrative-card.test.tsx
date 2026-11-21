import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

const state = vi.hoisted(() => ({ narrative: null as string | null | undefined, pending: false }));

vi.mock("@/lib/hooks/timeline", () => ({
  useCareerNarrative: () => ({
    isPending: state.pending,
    isSuccess: !state.pending && state.narrative != null,
    isError: false,
    data: { narrative: state.narrative },
    mutate: () => undefined,
  }),
}));

vi.mock("@/lib/i18n/locale-context", () => ({
  useLocale: () => ({ locale: "en", t: (key: string) => `[${key}]`, setLocale: () => undefined }),
}));

import { CareerNarrativeCard } from "./career-narrative-card";

const events = [{ at: "2026-11-03", kind: "application", title: "applied", refId: "x", summary: "" }];

describe("CareerNarrativeCard", () => {
  it("renders the action from locale keys and stays quiet before a request", () => {
    state.narrative = undefined;
    const html = renderToStaticMarkup(<CareerNarrativeCard events={events} />);
    expect(html).toContain("[timeline.narrativeTitle]");
    expect(html).toContain("[timeline.narrativeAction]");
    expect(html).not.toContain("[timeline.narrativeEmpty]");
  });

  it("disables the action when there are no events", () => {
    const html = renderToStaticMarkup(<CareerNarrativeCard events={[]} />);
    expect(html).toContain("disabled");
  });

  it("shows a grounded narrative once it arrives", () => {
    state.narrative = "The search ran from 2026-11-03 onward.";
    const html = renderToStaticMarkup(<CareerNarrativeCard events={events} />);
    expect(html).toContain("2026-11-03");
  });
});
