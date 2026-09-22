import { describe, expect, it, vi } from "vitest";

import { dispatchEvent, findFrameEnd, parseFrame, type SSEEvent } from "@/lib/sse/use-sse";

describe("parseFrame", () => {
  it("reads a bare string data frame", () => {
    expect(parseFrame("data: hello")).toEqual({ event: "message", data: "hello" });
  });
  it("parses JSON payloads", () => {
    expect(parseFrame('data: {"a":1}')).toEqual({ event: "message", data: { a: 1 } });
  });
  it("honours an explicit event name", () => {
    expect(parseFrame('event: token\ndata: "hi"')).toEqual({ event: "token", data: "hi" });
  });
  it("joins multi-line data with newlines", () => {
    expect(parseFrame("data: line1\ndata: line2")).toEqual({ event: "message", data: "line1\nline2" });
  });
  it("does not require a space after the colon", () => {
    expect(parseFrame("data:x")).toEqual({ event: "message", data: "x" });
  });
  it("handles CRLF line endings", () => {
    expect(parseFrame('event: status\r\ndata: {"ok":true}')).toEqual({ event: "status", data: { ok: true } });
  });
  it("ignores comment / keep-alive frames", () => {
    expect(parseFrame(": keep-alive")).toBeNull();
  });
  it("keeps a non-message event even without data", () => {
    expect(parseFrame("event: done")).toEqual({ event: "done", data: "" });
  });
});

describe("findFrameEnd", () => {
  it("finds a \\n\\n boundary", () => {
    expect(findFrameEnd("a\n\nb")).toBe(1);
  });
  it("finds a \\r\\n\\r\\n boundary", () => {
    expect(findFrameEnd("a\r\n\r\nb")).toBe(1);
  });
  it("returns the earliest of mixed boundaries", () => {
    // "\r\n\r\n" at index 0, "\n\n" at index 2
    expect(findFrameEnd("\r\n\r\nx\n\ny")).toBe(0);
  });
  it("returns -1 when there is no frame terminator", () => {
    expect(findFrameEnd("partial data")).toBe(-1);
  });
});

function handlers() {
  return {
    onStatus: vi.fn(),
    onToken: vi.fn(),
    onTrace: vi.fn(),
    onArtifact: vi.fn(),
    onDone: vi.fn(),
    onMessage: vi.fn(),
    onError: vi.fn(),
  };
}

describe("dispatchEvent", () => {
  it("routes named events to their handlers", () => {
    const cases: [SSEEvent, keyof ReturnType<typeof handlers>, unknown[]][] = [
      [{ event: "token", data: "hi" }, "onToken", ["hi"]],
      [{ event: "token", data: { token: "x" } }, "onToken", ["x"]],
      [{ event: "status", data: { progress: 1 } }, "onStatus", [{ progress: 1 }]],
      [{ event: "trace", data: { kind: "k" } }, "onTrace", [{ kind: "k" }]],
      [{ event: "artifact", data: { k: 1 } }, "onArtifact", [{ k: 1 }]],
      [{ event: "done", data: { ok: true } }, "onDone", [{ ok: true }]],
      [{ event: "error", data: { code: "E" } }, "onError", [{ code: "E" }]],
    ];
    for (const [evt, fn, args] of cases) {
      const h = handlers();
      dispatchEvent(evt, h);
      expect(h[fn]).toHaveBeenCalledWith(...args);
    }
  });

  it("unwraps message frames into a synthetic token event", () => {
    const h = handlers();
    dispatchEvent({ event: "message", data: { type: "token", token: "abc" } }, h);
    expect(h.onMessage).toHaveBeenCalledWith({ type: "token", token: "abc" });
    expect(h.onToken).toHaveBeenCalledWith("abc");
  });

  it("treats a string message data as a token", () => {
    const h = handlers();
    dispatchEvent({ event: "message", data: { type: "token", data: "tok" } }, h);
    expect(h.onToken).toHaveBeenCalledWith("tok");
  });

  it("unwraps message status/trace payloads", () => {
    const h = handlers();
    dispatchEvent({ event: "message", data: { type: "status", data: { p: 2 } } }, h);
    expect(h.onStatus).toHaveBeenCalledWith({ p: 2 });
    dispatchEvent({ event: "message", data: { type: "trace", data: { t: 3 } } }, h);
    expect(h.onTrace).toHaveBeenCalledWith({ t: 3 });
  });

  it("emits only onMessage for an unrecognized message shape", () => {
    const h = handlers();
    dispatchEvent({ event: "message", data: { foo: 1 } }, h);
    expect(h.onMessage).toHaveBeenCalledWith({ foo: 1 });
    expect(h.onToken).not.toHaveBeenCalled();
    expect(h.onStatus).not.toHaveBeenCalled();
    expect(h.onTrace).not.toHaveBeenCalled();
  });

  it("ignores unknown event names", () => {
    const h = handlers();
    dispatchEvent({ event: "bogus" as SSEEvent["event"], data: {} }, h);
    expect(h.onMessage).not.toHaveBeenCalled();
  });
});
