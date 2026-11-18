import { describe, expect, it, vi } from "vitest";
import * as React from "react";
import { renderToStaticMarkup } from "react-dom/server";

/**
 * Epic 331 — the assistant's one proactive first step.
 * The card renders a CTA on first paint; the sentence appears only after the
 * mutation answers, so the first render never invents a claim of its own.
 */
const assistantHook: {
  data: { step?: string | null } | undefined;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  mutate: any;
  isPending: boolean;
  isError: boolean;
  error: unknown;
} = { data: undefined, mutate: vi.fn(), isPending: false, isError: false, error: undefined };

vi.mock("@/lib/hooks/assistant", () => ({
  useNextStep: () => assistantHook,
}));

import { NextStepCard } from "./next-step-card";
import { LocaleProvider } from "@/lib/i18n/locale-context";

function render(locale: "en" | "zh"): string {
  vi.stubGlobal("window", {
    localStorage: { getItem: () => locale, setItem: () => {} },
  });
  try {
    return renderToStaticMarkup(
      <LocaleProvider>
        <NextStepCard />
      </LocaleProvider>,
    );
  } finally {
    vi.unstubAllGlobals();
  }
}

describe("the assistant's first step card", () => {
  it("renders the ask-token CTA in both languages before the assistant speaks", () => {
    assistantHook.data = undefined;
    assistantHook.isPending = false;
    assistantHook.isError = false;
    const en = render("en");
    expect(en).toContain("first step");
    expect(en).toContain("Ask the assistant");
    expect(en).not.toContain("Yesterday's");

    const zh = render("zh");
    expect(zh).toContain("今日第一步");
    expect(zh).toContain("问助手");
  });

  it("renders the grounded sentence only after the mutation kept one", () => {
    assistantHook.data = { step: "Knock out the 1 due reminder first; the 3 sleepiest applications will keep." };
    const en = render("en");
    expect(en).toContain("1 due reminder");

    assistantHook.data = { step: "先处理那 1 个到期的提醒，再挑 3 个最久没动的投递补一封信。" };
    const zh = render("zh");
    expect(zh).toContain("1 个到期的提醒");

    assistantHook.data = { step: null };
    const quiet = render("en");
    expect(quiet).not.toContain("due reminder");
  });

  it("announces its own failure instead of lying", () => {
    assistantHook.data = undefined;
    assistantHook.isError = true;
    expect(render("en")).toContain("could not see your week");
    expect(render("zh")).toContain("读不到你的这一周");
  });
});
