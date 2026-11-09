import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

// The translator echoes the key with its holes, so a missing key is visible in the
// markup instead of silently rendering English prose this file would not notice.
vi.mock("@/lib/i18n/locale-context", () => ({
  useLocale: () => ({
    locale: "en",
    t: (key: string, vars?: Record<string, unknown>) =>
      vars ? `[${key}|${Object.values(vars).join(",")}]` : `[${key}]`,
    setLocale: () => {},
  }),
}));

const state = vi.hoisted(() => ({
  topology: {
    data: undefined as
      | {
          registry: string;
          services: Array<{
            name: string;
            instances: Array<{ instanceId: string; uri: string }>;
          }>;
        }
      | undefined,
    isPending: false,
    isError: false,
  },
}));

vi.mock("@/lib/hooks/monitoring", () => ({
  useServiceTopology: () => state.topology,
}));

import { ServiceTopology } from "./service-topology";

describe("ServiceTopology", () => {
  it("draws every service and instance the discovery client reported", () => {
    state.topology = {
      data: {
        registry: "eureka",
        services: [
          { name: "ai-service", instances: [{ instanceId: "ai-1", uri: "http://10.0.0.4:8000" }] },
          {
            name: "backend",
            instances: [
              { instanceId: "b-1", uri: "http://10.0.0.2:8080" },
              { instanceId: "b-2", uri: "http://10.0.0.3:8080" },
            ],
          },
        ],
      },
      isPending: false,
      isError: false,
    };

    const html = renderToStaticMarkup(<ServiceTopology />);

    expect(html).toContain("ai-service");
    expect(html).toContain("backend");
    expect(html).toContain("http://10.0.0.3:8080");
    expect(html).toContain("[monitoring.topologyRegistryEureka]");
    expect(html).toContain("[monitoring.topologyInstances|2]");
  });

  it("says the client knows no service rather than drawing an empty box", () => {
    state.topology = {
      data: { registry: "configuration", services: [] },
      isPending: false,
      isError: false,
    };

    const html = renderToStaticMarkup(<ServiceTopology />);

    expect(html).toContain("[monitoring.topologyEmpty]");
    expect(html).not.toContain("[monitoring.topologyRegistry]");
  });

  it("says the topology could not be read", () => {
    state.topology = { data: undefined, isPending: false, isError: true };

    const html = renderToStaticMarkup(<ServiceTopology />);

    expect(html).toContain("[monitoring.topologyUnavailable]");
  });
});
