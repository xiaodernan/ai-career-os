import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

import { AnswerEchoCard } from "./answer-echo-card";
import { LocaleProvider } from "@/lib/i18n/locale-context";

/**
 * Epic 385 — the echo card renders the arithmetic, in the reader's language, and
 * renders nothing at all before the first answer. The numbers themselves are the
 * pure module's tests; this file grades the surface.
 */
function render(answers: string[], locale: "en" | "zh" = "zh"): string {
  vi.stubGlobal("window", {
    localStorage: { getItem: () => locale, setItem: () => {} },
  });
  try {
    return renderToStaticMarkup(
      <LocaleProvider>
        <AnswerEchoCard answers={answers} />
      </LocaleProvider>
    );
  } finally {
    vi.unstubAllGlobals();
  }
}

describe("AnswerEchoCard", () => {
  it("renders nothing before the session has answered anything", () => {
    expect(render([])).toBe("");
    expect(render(["   "])).toBe("");
  });

  it("shows the counts and the repeated term in Chinese", () => {
    const markup = render(["嗯，我做了这个项目。"]);
    expect(markup).toContain("本机回声");
    expect(markup).toContain("回答数");
    expect(markup).toContain("填充词");
    expect(markup).toContain("嗯 × 1");
    expect(markup).toContain("没有调用模型");
  });

  it("names the plural voice to an English reader from the same arithmetic", () => {
    const markup = render(["We shipped it. We shipped it. We shipped it."], "en");
    expect(markup).toContain("The echo");
    expect(markup).toContain("outnumbers");
    expect(markup).toContain("\u201cWe\u201d");
    expect(markup).toContain("\u201cI\u201d");
  });

  it("says the arithmetic is clean when the answers carry length, figures and an I", () => {
    const markup = render(
      [
        "I cut p95 latency from 420 ms to 95 ms. I shipped the migration in three weeks. " +
          "I wrote the runbook the team still uses. I trained two engineers to own it. " +
          "I measured the result every morning for a month before I called it done.",
      ],
      "en"
    );
    expect(markup).toContain("No obvious arithmetic problem");
    expect(markup).toContain("100%");
  });
});
