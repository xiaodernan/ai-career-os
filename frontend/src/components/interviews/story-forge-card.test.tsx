import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

const forgeState = vi.hoisted(() => ({ data: null as unknown, isPending: false, mutate: vi.fn() }));

vi.mock("@/lib/hooks/growth", () => ({
  useStoryForge: () => forgeState,
}));

vi.mock("@/lib/i18n/locale-context", () => ({
  useLocale: () => ({
    locale: "en",
    t: (key: string) => `[${key}]`,
    setLocale: () => undefined,
  }),
}));

import { StoryForgeCard } from "./story-forge-card";

describe("StoryForgeCard", () => {
  it("renders the forge controls from locale keys, with no hard-coded English copy", () => {
    forgeState.data = null;
    forgeState.isPending = false;
    const html = renderToStaticMarkup(<StoryForgeCard />);
    expect(html).toContain("[storyForge.title]");
    expect(html).toContain("[storyForge.label]");
    expect(html).toContain("[storyForge.action]");
    expect(html).toContain("story-forge-note");
    // No result panel before a call.
    expect(html).not.toContain("[storyForge.storyTitle]");
  });

  it("shows the story fields, honest follow-ups and struck figures from the engine", () => {
    forgeState.data = {
      story: { situation: "S", task: "T", action: "A", result: "R" },
      open: [{ question: "How exactly?", reason: "vague" }],
      closed: [],
      struck_fields: ["result"],
      complete: false,
      locale: "en",
    };
    const html = renderToStaticMarkup(<StoryForgeCard />);
    expect(html).toContain("[storyForge.incomplete]");
    expect(html).toContain("[storyForge.storyTitle]");
    expect(html).toContain("[storyForge.situation]");
    expect(html).toContain("[storyForge.resultLabel]");
    expect(html).toContain("How exactly?");
    expect(html).toContain("[storyForge.followupsTitle]");
    expect(html).toContain("[storyForge.struckTitle]");
    expect(html).toContain("[storyForge.struckHint]");
  });

  it("shows the ready copy when the story is complete", () => {
    forgeState.data = {
      story: { situation: "S", task: "T", action: "A", result: "R" },
      open: [], closed: [], struck_fields: [], complete: true, locale: "zh",
    };
    const html = renderToStaticMarkup(<StoryForgeCard />);
    expect(html).toContain("[storyForge.complete]");
    expect(html).not.toContain("[storyForge.followupsTitle]");
  });
});
