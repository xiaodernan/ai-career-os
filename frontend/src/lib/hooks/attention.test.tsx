import { afterEach, describe, expect, it, vi } from "vitest";

import { trackAct } from "./attention";

describe("trackAct", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("posts exactly one anonymous act, carrying only the path", () => {
    const calls: Array<{ url: string; init: RequestInit }> = [];
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string, init: RequestInit) => {
        calls.push({ url, init });
        return Promise.resolve({});
      }),
    );

    trackAct("/", "public");

    expect(calls).toHaveLength(1);
    const { url, init } = calls[0];
    expect(url).toContain("/telemetry/attention");
    expect(init.method).toBe("POST");
    expect(init.keepalive).toBe(true);
    const body = JSON.parse(String(init.body));
    expect(body).toEqual({ journey: "public", path: "/", event: "act" });
    // the signal is anonymous by construction: no id, no user field, no value
    expect(Object.keys(body).sort()).toEqual(["event", "journey", "path"]);
  });

  it("defaults to the app journey and survives a network that refuses to answer", () => {
    const bodies: string[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn((_url: string, init: RequestInit) => {
        bodies.push(String(init.body));
        return Promise.reject(new Error("offline"));
      }),
    );

    expect(() => trackAct("/applications")).not.toThrow();
    expect(JSON.parse(bodies[0])).toEqual({ journey: "app", path: "/applications", event: "act" });
  });

  it("swallows a synchronous throw the way the sensor swallows them", () => {
    vi.stubGlobal("fetch", vi.fn(() => {
      throw new Error("detached realm");
    }));
    expect(() => trackAct("/", "public")).not.toThrow();
  });
});
