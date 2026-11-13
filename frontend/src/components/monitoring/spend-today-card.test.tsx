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

import { SpendTodayCard } from "./spend-today-card";

describe("SpendTodayCard (21.x)", () => {
  it("renders the day's total, the cap progress and the three sub-readings", () => {
    const html = renderToStaticMarkup(
      <SpendTodayCard
        pending={false}
        error={null}
        onRetry={() => {}}
        spend={{
          dayStart: "2026-11-13T00:00Z",
          costUsd: 0.002655,
          inputTokens: 9994,
          outputTokens: 820,
          cachedTokens: 4997,
          calls: 2,
          cacheHitRatio: 0.5,
          capUsd: 10.0,
          capEnabled: true,
          capExceeded: false,
        }}
      />
    );

    expect(html).toContain("$0.0027");
    expect(html).toContain("[monitoring.spendTodayCalls|2]");
    expect(html).toContain("[monitoring.spendTodayOfCap|10.00]");
    expect(html).toContain("9,994");
    expect(html).toContain("4,997");
    expect(html).toContain("50%");
    expect(html).toContain("role=\"progressbar\"");
  });

  it("an exhausted cap reads as the destructive state, not a silently-full bar", () => {
    const html = renderToStaticMarkup(
      <SpendTodayCard
        pending={false}
        error={null}
        onRetry={() => {}}
        spend={{
          costUsd: 10.0,
          inputTokens: 9994,
          cachedTokens: 0,
          calls: 9,
          cacheHitRatio: 0.0,
          capUsd: 10.0,
          capEnabled: true,
          capExceeded: true,
        }}
      />
    );

    expect(html).toContain("bg-destructive");
    expect(html).toContain("[monitoring.spendTodayCalls|9]");
  });

  it("cap = 0 removes the bar and says so, instead of rendering a fake full one", () => {
    const html = renderToStaticMarkup(
      <SpendTodayCard
        pending={false}
        error={null}
        onRetry={() => {}}
        spend={{
          costUsd: 0.42,
          inputTokens: 1000,
          outputTokens: 100,
          cachedTokens: 400,
          calls: 4,
          cacheHitRatio: 0.4,
          capUsd: 0,
          capEnabled: false,
          capExceeded: false,
        }}
      />
    );

    expect(html).not.toContain("role=\"progressbar\"");
    expect(html).toContain("[monitoring.spendTodayNoCap]");
  });

  it("says pending before it says anything about money", () => {
    const html = renderToStaticMarkup(
      <SpendTodayCard pending error={null} onRetry={() => {}} spend={undefined} />
    );

    expect(html).toContain("[monitoring.spendToday]");
    expect(html).not.toContain("$0.0000");
  });

  it("a failed read offers the reader a retry, not a card full of zeros", () => {
    const html = renderToStaticMarkup(
      <SpendTodayCard pending={false} error={new Error("boom")} onRetry={() => {}} spend={undefined} />
    );

    expect(html).toContain("[monitoring.spendTodayFailed]");
    expect(html).not.toContain("$0.0000");
  });
});
