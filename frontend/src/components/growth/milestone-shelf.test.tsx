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
    milestones: Array<{ key: string; done: boolean; progress: number | null; target: number | null }>;
    counters: {
      applications: number;
      interviewsCompleted: number;
      offers: number;
      letters: number;
      matches: number;
      currentStreak: number;
      offersOnShelf: number;
    };
  },
}));

vi.mock("@/lib/hooks/monitoring", () => ({
  useMilestones: () =>
    state.data ? { data: state.data, isPending: false, isError: false } : { data: undefined, isPending: true, isError: false },
}));

import { MilestoneShelf } from "./milestone-shelf";

describe("MilestoneShelf", () => {
  it("shows the skeleton while the shelf is pending", () => {
    const html = renderToStaticMarkup(<MilestoneShelf />);
    expect(html).toContain('data-slot="skeleton"');
  });

  it("renders earned and working badges differently, with the real numbers", () => {
    state.data = {
      milestones: [
        { key: "first_step", done: true, progress: null, target: 1 },
        { key: "fifty_steps", done: false, progress: 10, target: 50 },
      ],
      counters: {
        applications: 10,
        interviewsCompleted: 2,
        offers: 0,
        letters: 1,
        matches: 1,
        currentStreak: 3,
        offersOnShelf: 0,
      },
    };

    const html = renderToStaticMarkup(<MilestoneShelf />);

    // Earned/working wording comes from the locale table, not a hard-coded English map,
    // so a Chinese reader never sees an English sentence (copy-census gate). The mock's
    // t() echoes the key, which is exactly what we assert here.
    expect(html).toContain("[growth.milestone_first_step_earned]");
    expect(html).toContain("[growth.milestone_fifty_steps_working]");
    expect(html).toContain('aria-valuenow="10"');
    expect(html).toContain("width:20%");
    expect(html).toContain("[growth.milestoneProgress|10,50]");
    expect(html).toContain("[growth.milestoneEarned]");
    // The counters line quotes the backend's own numbers, not invented ones.
    expect(html).toContain("[growth.milestoneCounters|10,2,0]");
  });

  it("hides the progress bar for single-shot milestones still being worked", () => {
    state.data = {
      milestones: [{ key: "first_offer", done: false, progress: 0, target: 1 }],
      counters: {
        applications: 0,
        interviewsCompleted: 0,
        offers: 0,
        letters: 0,
        matches: 0,
        currentStreak: 0,
        offersOnShelf: 0,
      },
    };

    const html = renderToStaticMarkup(<MilestoneShelf />);
    expect(html).toContain("[growth.milestone_first_offer_working]");
    expect(html).not.toContain("role=\"progressbar\"");
  });
});
