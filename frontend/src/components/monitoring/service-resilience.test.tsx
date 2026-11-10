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

const state = vi.hoisted(() => ({
  resilience: {
    data: undefined as
      | {
          circuitBreakers: Array<{
            name: string;
            state: string;
            numberOfFailedCalls?: number;
            numberOfSuccessfulCalls?: number;
            numberOfNotPermittedCalls?: number;
          }>;
        }
      | undefined,
    isPending: false,
    isError: false,
  },
}));

vi.mock("@/lib/hooks/monitoring", () => ({
  useServiceResilience: () => state.resilience,
}));

import { ServiceResilience } from "./service-resilience";

describe("ServiceResilience", () => {
  it("draws circuit breakers and their states", () => {
    state.resilience = {
      data: {
        circuitBreakers: [
          { name: "ai-service", state: "CLOSED", numberOfFailedCalls: 0, numberOfSuccessfulCalls: 3, numberOfNotPermittedCalls: 0 },
          { name: "ai-service:https://engine-a:8000", state: "OPEN", numberOfFailedCalls: 5, numberOfSuccessfulCalls: 1, numberOfNotPermittedCalls: 2 },
        ],
      },
      isPending: false,
      isError: false,
    };

    const html = renderToStaticMarkup(<ServiceResilience />);

    expect(html).toContain("ai-service");
    expect(html).toContain("CLOSED");
    expect(html).toContain("OPEN");
    expect(html).toContain("[monitoring.resilienceCalls|0,3,0]");
  });

  it("says there are no breakers yet", () => {
    state.resilience = { data: { circuitBreakers: [] }, isPending: false, isError: false };
    const html = renderToStaticMarkup(<ServiceResilience />);
    expect(html).toContain("[monitoring.resilienceEmpty]");
  });

  it("says resilience could not be read", () => {
    state.resilience = { data: undefined, isPending: false, isError: true };
    const html = renderToStaticMarkup(<ServiceResilience />);
    expect(html).toContain("[monitoring.resilienceUnavailable]");
  });

  it("shows a loading skeleton while pending", () => {
    state.resilience = { data: undefined, isPending: true, isError: false };
    const html = renderToStaticMarkup(<ServiceResilience />);
    expect(html).toContain("shimmer");
  });
});