"use client";

import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { Sparkles } from "lucide-react";

import { EmptyComposition } from "./empty-composition";
import { EmptyState } from "./empty-state";

vi.mock("@/lib/i18n/locale-context", () => ({
  useLocale: () => ({
    locale: "en",
    t: (key: string) => key,
    setLocale: () => undefined,
  }),
}));

describe("EmptyComposition", () => {
  it("renders the promise eyebrow, the title, the CTA and the proofs — in the markup, before any animation", () => {
    const markup = renderToStaticMarkup(
      <EmptyComposition
        icon={<Sparkles aria-hidden />}
        promise="WHAT THE TRACE TELLS YOU"
        title="No agent runs yet"
        description="Once Copilot or a matching job runs, its full trace appears here."
        action={<button type="button">Open Copilot</button>}
        proofs={["Every model call in order", "A cached call shows its savings"]}
      />,
    );
    expect(markup).toContain("WHAT THE TRACE TELLS YOU");
    expect(markup).toContain("No agent runs yet");
    expect(markup).toContain("Once Copilot or a matching job runs");
    expect(markup).toContain("Open Copilot");
    expect(markup).toContain("Every model call in order");
    expect(markup).toContain("A cached call shows its savings");
  });

  it("caps the proof list at three — a surface smaller than its claim is honest", () => {
    const markup = renderToStaticMarkup(
      <EmptyComposition
        icon={<Sparkles aria-hidden />}
        title="x"
        proofs={["one", "two", "three", "four", "five"]}
      />,
    );
    expect((markup.match(/<li/g) ?? []).length).toBe(3);
    expect(markup).not.toContain("four");
  });

  it("omits the eyebrow and the proof list when the caller has none to make — never a placeholder", () => {
    const markup = renderToStaticMarkup(
      <EmptyComposition icon={<Sparkles aria-hidden />} title="quiet" description="the sentence" />,
    );
    expect(markup).toContain("quiet");
    expect(markup).not.toContain("<ul");
  });
});

describe("EmptyState — the Epic 3 hand-off", () => {
  it("delegates to the composition when the surface passes a promise or proofs", () => {
    const markup = renderToStaticMarkup(
      <EmptyState
        icon={<Sparkles aria-hidden />}
        promise="WHAT ONE CARD BECOMES"
        proofs={["one", "two"]}
        title="Pipeline is empty"
        description="Track a job and it appears here."
        action={<button type="button">Add application</button>}
      />,
    );
    expect(markup).toContain("WHAT ONE CARD BECOMES");
    expect(markup).toContain("one");
    expect(markup).toContain("Add application");
  });

  it("keeps the compact layout for a surface that passes neither (the long tail)", () => {
    const markup = renderToStaticMarkup(
      <EmptyState icon={<Sparkles aria-hidden />} title="quiet" description="plain" />,
    );
    expect(markup).toContain("quiet");
    expect(markup).not.toContain("WHAT");
  });
});
