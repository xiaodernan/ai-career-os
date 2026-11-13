"use client";

import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

vi.mock("@/lib/i18n/locale-context", () => ({
  useLocale: () => ({
    locale: "en",
    t: (key: string, vars?: Record<string, unknown>) =>
      vars ? `[${key}|${Object.values(vars).join(",")}]` : `[${key}]`,
    setLocale: () => {},
  }),
}));
vi.mock("@/lib/trace-kinds", () => ({
  asTraceKind: (v: unknown) => String(v ?? ""),
  TRACE_KINDS: [],
}));

import { AgentTraceEvent, AgentTimeline } from "./agent-timeline";

describe("AgentTimeline — the llm_call row says its transport", () => {
  it("renders a stream chip on streamed model calls and a complete chip on blocking ones", () => {
    const markup = renderToStaticMarkup(
      <AgentTimeline
        events={[
          {
            id: "r1",
            kind: "llm_call",
            label: "jd_analyze · gpt-6-sol",
            payload: { kind: "jd_analyze", model: "gpt-6-sol", mode: "stream" },
          },
          {
            id: "r2",
            kind: "llm_call",
            label: "step_2 · gpt-6-sol",
            payload: { kind: "step_2", model: "gpt-6-sol", mode: "stream" },
          },
          {
            id: "r3",
            kind: "llm_call",
            label: "rerank · gpt-6-sol",
            payload: { kind: "rerank", model: "gpt-6-sol", mode: "complete" },
          },
        ]}
      />
    );

    expect((markup.match(/>stream</g) ?? []).length).toBe(2);
    expect((markup.match(/>complete</g) ?? []).length).toBe(1);
  });

  it("stays quiet on a row whose llm_call carries no mode at all", () => {
    const markup = renderToStaticMarkup(
      <AgentTimeline
        events={[
          {
            id: "r4",
            kind: "llm_call",
            label: "jd_analyze",
            payload: { kind: "jd_analyze" },
          },
        ]}
      />
    );

    expect(markup).not.toContain(">stream<");
    expect(markup).not.toContain(">complete<");
  });
});
