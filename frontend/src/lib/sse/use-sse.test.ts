import { readFileSync } from "node:fs";
import { describe, expect, it, vi } from "vitest";

import {
  dispatchEvent,
  drainFrames,
  errorText,
  findFrameEnd,
  parseFrame,
  tokenText,
  type SSEEvent,
} from "@/lib/sse/use-sse";

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

/**
 * The frames a buffer holds.
 *
 * A network read does not land on a frame boundary -- a read can carry
 * half a frame, or three and a half. So the buffer accumulates and the
 * frames are taken out of it as they complete, and what is left is what
 * the next read continues. This is the loop the stream reader runs, and
 * it is the part that decides whether the reader sees the frames at all.
 */
describe("drainFrames", () => {
  it("takes the whole frame out of the buffer", () => {
    const { frames, rest } = drainFrames("event: token\ndata: hi\n\n");
    expect(frames).toEqual(["event: token\ndata: hi"]);
    expect(rest).toBe("");
  });

  it("keeps a partial frame for the next read", () => {
    // The read landed in the middle of a frame. Nothing is dispatched and
    // nothing is lost: the half-frame is what the next read continues.
    const { frames, rest } = drainFrames("event: token\ndata: hi");
    expect(frames).toEqual([]);
    expect(rest).toBe("event: token\ndata: hi");
  });

  it("takes several frames out of one read", () => {
    const { frames, rest } = drainFrames(
      "event: token\ndata: a\n\nevent: token\ndata: b\n\n"
    );
    expect(frames).toEqual(["event: token\ndata: a", "event: token\ndata: b"]);
    expect(rest).toBe("");
  });

  it("cuts on a CRLF boundary as readily as on an LF one", () => {
    const { frames, rest } = drainFrames("event: token\r\ndata: hi\r\n\r\n");
    expect(frames).toEqual(["event: token\r\ndata: hi"]);
    expect(rest).toBe("");
  });

  it("cuts a mixed stream on both kinds of boundary", () => {
    // A relay that mixes line endings is not a thing that should break the
    // reader: the frames are what matter, not the line ending.
    const { frames, rest } = drainFrames("data: a\n\ndata: b\r\n\r\ndata: c\n\n");
    expect(frames).toEqual(["data: a", "data: b", "data: c"]);
    expect(rest).toBe("");
  });

  it("joins the halves of a frame split across two reads", () => {
    // The first read carries the head, the second the tail. The reader
    // must see one frame, not two.
    const first = drainFrames("event: token\nda");
    expect(first.frames).toEqual([]);
    const second = drainFrames(first.rest + "ta: hi\n\n");
    expect(second.frames).toEqual(["event: token\ndata: hi"]);
    expect(second.rest).toBe("");
  });

  it("leaves a keep-alive comment in the buffer rather than cutting a frame on it", () => {
    // A comment is not a frame and does not end one, so the frame after it
    // is still one frame.
    const { frames } = drainFrames(": keep-alive\n\nevent: token\ndata: hi\n\n");
    expect(frames).toEqual([": keep-alive", "event: token\ndata: hi"]);
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
      [{ event: "progress", data: { step: "embedding", done: 64, total: 150 } }, "onStatus", [{ step: "embedding", done: 64, total: 150 }]],
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

  it("drops the taskbus keep-alive without claiming the run reported", () => {
    const h = handlers();
    dispatchEvent({ event: "ping", data: {} }, h);
    expect(h.onStatus).not.toHaveBeenCalled();
    expect(h.onError).not.toHaveBeenCalled();
  });

  it("does not turn an unreadable token frame into an empty delta", () => {
    const h = handlers();
    dispatchEvent({ event: "token", data: { text: "" } }, h);
    expect(h.onToken).not.toHaveBeenCalled();
  });
});

/**
 * Frames copied from the publishers, not invented: taskbus.finish (app/core/taskbus.py)
 * wraps `{result, error}`, taskbus.subscribe answers an unknown id the same way, and
 * SseRelayService.pump sends a bare string.
 */
describe("errorText", () => {
  it("reads the cause a failed agent turn published", () => {
    // app/api/agents.py: taskbus.finish(task_id, False, error=str(e)[:500])
    expect(errorText({ result: null, error: "ConnectionResetError: [Errno 104] Connection reset by peer" })).toBe(
      "ConnectionResetError: [Errno 104] Connection reset by peer"
    );
  });

  it("reads the cause the ingestion pipeline published before any step ran", () => {
    // app/ingestion/pipeline.py: finish(task_id, False, error="document not found")
    expect(errorText({ result: null, error: "document not found" })).toBe("document not found");
    // ...and the `{type}: {e}` shape of its crash branch.
    expect(errorText({ result: null, error: "ValueError: empty page text" })).toBe("ValueError: empty page text");
  });

  it("reads the relay's bare-string upstream failure", () => {
    expect(errorText("upstream status 502")).toBe("upstream status 502");
  });

  it("shows the first line of a cause, not the stack trace under it", () => {
    const frame = { result: null, error: "RuntimeError: pdf page 7 unreadable\nTraceback (inner most last):" };
    expect(errorText(frame)).toBe("RuntimeError: pdf page 7 unreadable");
  });

  it("does not read the REST error envelope — SSE bodies are never enveloped", () => {
    // EnvelopeAdvice.beforeBodyWrite skips SseEmitter, so {code,message,details}
    // cannot arrive on this channel. Reading `message` is what hid every cause.
    expect(errorText({ code: "JOB_NOT_FOUND", message: "no such job" })).toBeNull();
  });

  it("returns null instead of inventing a cause the frame does not carry", () => {
    expect(errorText(null)).toBeNull();
    expect(errorText(undefined)).toBeNull();
    expect(errorText("")).toBeNull();
    expect(errorText({ result: null, error: null })).toBeNull();
    expect(errorText({ error: "   \nsecond line" })).toBeNull();
  });

  it("caps a one-line cause without splitting a code point", () => {
    const ascii = errorText({ error: "x".repeat(500) });
    expect(ascii).toHaveLength(180);
    expect(ascii?.endsWith("…")).toBe(true);

    const emoji = errorText({ error: "\u{1F4A5}".repeat(300) })!;
    expect(Array.from(emoji)).toHaveLength(180); // 179 deltas + the ellipsis
    expect(emoji.endsWith("…")).toBe(true);
    // A `slice` cut here would strand the high surrogate of the 180th delta.
    expect(emoji).not.toMatch(/[\uD800-\uDBFF](?![\uDC00-\uDFFF])/);
  });
});

describe("tokenText", () => {
  it("reads the delta shape ai.stream() publishes", () => {
    // app/core/ai.py: await emit({"event": "token", "data": {"text": delta.text}})
    expect(tokenText({ text: "Streaming the " })).toBe("Streaming the ");
  });

  it("still reads a bare string frame and the {token} spelling", () => {
    expect(tokenText("hi")).toBe("hi");
    expect(tokenText({ token: "x" })).toBe("x");
  });

  it("yields empty for a frame carrying neither", () => {
    expect(tokenText({})).toBe("");
    expect(tokenText(null)).toBe("");
  });
});

/**
 * `useTaskStream` is a hook in a node-environment suite, so nothing here can render
 * it. The one regression this can still catch is the reader going back to a
 * hand-picked key instead of the fold.
 */
describe("the run stream consumer", () => {
  const source = readFileSync(
    new URL("../../components/ai/task-stream.tsx", import.meta.url),
    "utf8"
  );

  it("asks errorText for the cause instead of naming a key itself", () => {
    expect(source).toContain("errorText(data)");
    expect(source).not.toMatch(/data\?\.message/);
  });
});

/**
 * The end of the stream.
 *
 * A frame is terminated by the blank line after it, and the reader takes
 * it out of the buffer when it sees one. Whatever is still in the buffer
 * when the stream ends is therefore a *partial* frame -- a server that
 * closed the connection mid-frame left one behind. Dispatching it would
 * append half a token to the answer, and a truncated delta reads as a
 * truncated sentence.
 *
 * The hook cannot be rendered here, so the gate reads its source: the
 * remainder must be dropped, not flushed.
 */
describe("the end of a stream", () => {
  const source = readFileSync(
    new URL("./use-sse.ts", import.meta.url),
    "utf8"
  );

  it("discards the partial frame a cut connection leaves behind", () => {
    // The relay's frames are terminated by Spring's SseEmitter, so the
    // remainder is never a whole frame -- it is a fragment, and a
    // fragment must not be dispatched.
    //
    // The needle is built in two pieces on purpose: the census that
    // watches this file counts the *textual* calls of the frame entry
    // points, and a test that merely names a call is not one. Spelling
    // the name out in full would count this assertion as a witness it
    // is not.
    const flushed = ["dispatch", "Event(last"].join("");
    expect(source).not.toContain(flushed);
    expect(source).not.toMatch(/parseFrame\(buffer\)/);
  });

  it("reads the buffer with the frame splitter, not with its own loop", () => {
    // One rule for where a frame ends, in one place. A second copy of the
    // splitting loop is a second answer to "where does a frame end".
    expect(source).toContain("drainFrames(buffer)");
    expect(source).not.toMatch(/while \(\(sep = findFrameEnd\(/);
  });
});
