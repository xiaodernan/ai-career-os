import { afterEach, describe, expect, it, vi } from "vitest";

import { trackAct, leaveRoom } from "./attention";

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

describe("leaveRoom — impatient bounce vs an honest dwell", () => {
  afterEach(() => vi.unstubAllGlobals());

  function capture(): { calls: Array<Record<string, unknown>> } {
    const calls: Array<Record<string, unknown>> = [];
    vi.stubGlobal("fetch", vi.fn((_url: string, init: RequestInit) => {
      calls.push(JSON.parse(String(init.body)));
      return Promise.resolve({});
    }));
    return { calls };
  }

  it("records a bounce with the time-on-page when the reader left early", () => {
    const { calls } = capture();
    const now = Date.now();
    // Force a short stay by anchoring `start` in the near future is not possible; instead
    // use a start so that Date.now()-start is small (the call happens immediately).
    leaveRoom("/jobs", now, "app", true, { done: false });
    expect(calls).toHaveLength(1);
    expect(calls[0].event).toBe("bounce");
    expect(calls[0].path).toBe("/jobs");
    expect(Number(calls[0].value)).toBeGreaterThanOrEqual(0);
    expect(Number(calls[0].value)).toBeLessThan(4_000);
  });

  it("records an honest dwell when the reader stayed", () => {
    const { calls } = capture();
    leaveRoom("/jobs", Date.now() - 30_000, "app", false, { done: false });
    expect(calls).toHaveLength(1);
    expect(calls[0].event).toBe("dwell");
    expect(Number(calls[0].value)).toBeGreaterThanOrEqual(30_000);
  });

  it("never double-counts a visit that both hid and unmounted", () => {
    const { calls } = capture();
    const reported = { done: false };
    leaveRoom("/jobs", Date.now(), "app", true, reported);
    leaveRoom("/jobs", Date.now(), "app", false, reported);
    expect(calls).toHaveLength(1);
  });
});
