import { describe, expect, it, vi } from "vitest";
import * as React from "react";
import { renderToStaticMarkup } from "react-dom/server";

/**
 * The gap card (10.1) in the granular panel. Epic 329 adds the analyst's one
 * grounded paragraph beneath the coverage line — it renders only when the
 * engine kept one, in the reader's own language, and stays absent otherwise.
 */
const GAP_ANSWER = {
  targetRole: "Senior Backend Engineer (Java)",
  expectedSkillCount: 1,
  coveredCount: 1,
  partialCount: 0,
  gapCount: 0,
  coverage: 1.0,
  gaps: [],
  strengths: ["Java"],
  note: null as string | null,
};

const NOTE_EN =
  "I have full coverage at 1.0, with 1 of 1 expected skills covered and 0 gaps.";
const NOTE_ZH =
  "覆盖率为 1.0，预期技能 1 项中已覆盖 1 项，部分匹配 0 项，缺失 0 项。";

vi.mock("@/lib/hooks/growth", () => {
  // Defined inside the factory: a module-scope helper would be in the temporal
  // dead zone when vitest evaluates this mock.
  const idle = () => ({
    data: undefined,
    mutate: vi.fn(),
    isPending: false,
    isError: false,
    error: undefined,
  });
  return {
    useGapAnalysis: () => idle(),
    useGapNote: () => gapHook,
    useInterviewPrep: () => idle(),
    useLearningPlan: () => idle(),
    useLearningPriority: () => idle(),
    useProgression: () => idle(),
    useRoleSuggestions: () => idle(),
    useSkillDemand: () => idle(),
    useSkillProgress: () => idle(),
    useStoryBank: () => idle(),
  };
});

vi.mock("@/lib/hooks/actions", () => ({
  useCreateInterviewSession: () => ({ mutate: vi.fn(), isPending: false }),
}));

const gapHook: {
  data: typeof GAP_ANSWER | undefined;
  mutate: ReturnType<typeof vi.fn>;
  isPending: boolean;
  isError: boolean;
  error: unknown;
} = { data: { ...GAP_ANSWER }, mutate: vi.fn(), isPending: false, isError: false, error: undefined };

import { GrowthEnginesPanel } from "./growth-engines-panel";
import { LocaleProvider } from "@/lib/i18n/locale-context";

function render(locale: "en" | "zh"): string {
  vi.stubGlobal("window", {
    localStorage: { getItem: () => locale, setItem: () => {} },
  });
  try {
    return renderToStaticMarkup(
      <LocaleProvider>
        <GrowthEnginesPanel />
      </LocaleProvider>,
    );
  } finally {
    vi.unstubAllGlobals();
  }
}

describe("the gap card's analyst paragraph", () => {
  it("renders the grounded note under the coverage line when the engine kept one", () => {
    gapHook.data = { ...GAP_ANSWER, note: NOTE_EN };
    const en = render("en");
    expect(en).toContain("The analyst says");
    expect(en).toContain(NOTE_EN);

    gapHook.data = { ...GAP_ANSWER, note: NOTE_ZH };
    const zh = render("zh");
    expect(zh).toContain("分析师说");
    expect(zh).toContain(NOTE_ZH);
  });

  it("stays absent when the editor kept no grounded paragraph", () => {
    gapHook.data = { ...GAP_ANSWER, note: null };
    const en = render("en");
    expect(en).not.toContain("The analyst says");
    expect(en).toContain("100%");

    gapHook.data = { ...GAP_ANSWER, note: undefined as unknown as null };
    const zh = render("zh");
    expect(zh).not.toContain("分析师说");
  });
});
