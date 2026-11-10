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
  health: {
    data: undefined as
      | { status: string; ai?: boolean; aiNodes?: Array<{ url: string; up: boolean }> }
      | undefined,
    isPending: false,
    isError: false,
  },
}));

vi.mock("@/lib/hooks/monitoring", () => ({
  useDeploymentHealth: () => state.health,
}));

import { ServiceEngines } from "./service-engines";

describe("ServiceEngines", () => {
  it("lists every configured engine replica and how the probe sees it", () => {
    state.health = {
      data: {
        status: "ok",
        ai: true,
        aiNodes: [
          { url: "http://engine-a:8000", up: true },
          { url: "http://engine-b:8000", up: false },
        ],
      },
      isPending: false,
      isError: false,
    };

    const html = renderToStaticMarkup(<ServiceEngines />);

    expect(html).toContain("engine-a");
    expect(html).toContain("engine-b");
    expect(html).toContain("UP");
    expect(html).toContain("DOWN");
    expect(html).toContain("[monitoring.enginesReady|1,2]");
  });

  it("says no replica answered the probe", () => {
    state.health = {
      data: { status: "degraded", ai: false, aiNodes: [] },
      isPending: false,
      isError: false,
    };

    const html = renderToStaticMarkup(<ServiceEngines />);

    expect(html).toContain("[monitoring.enginesEmpty]");
  });

  it("says engine health could not be read", () => {
    state.health = { data: undefined, isPending: false, isError: true };

    const html = renderToStaticMarkup(<ServiceEngines />);

    expect(html).toContain("[monitoring.enginesUnavailable]");
  });
});