"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { API_BASE_URL } from "@/lib/api/endpoints";
import { tokenStore } from "@/lib/api/token-store";
import type { SSEEventName } from "@/lib/api/types";

export interface SSEEvent {
  /**
   * The backend relay forwards upstream event names verbatim
   * (SseRelayService.relayEvents), so the two names the pipelines actually send
   * outside architecture.md §9's list reach the client too: `progress` from the
   * ingestion pipeline and `ping`, the idle keep-alive from taskbus.subscribe.
   */
  event: SSEEventName | "message" | "progress" | "ping";
  data: unknown;
}

export interface UseSSEOptions {
  /** Absolute URL or path resolved against the API base. Pass null to disable. */
  url: string | null;
  /** SSE event names emitted by the backend (architecture.md §9) */
  onStatus?: (data: SSEStatusData) => void;
  onToken?: (token: string) => void;
  onTrace?: (data: SSETraceData) => void;
  onArtifact?: (data: unknown) => void;
  onDone?: (data: unknown) => void;
  /** `message` frames — the relay's generic JSON channel (status/token payload). */
  onMessage?: (data: unknown) => void;
  /**
   * Failure frame, raw. Turn it into a sentence with {@link errorText} — the shape
   * is `{error}` or a bare string, not the REST `{code,message,details}` envelope,
   * because EnvelopeAdvice skips SseEmitter and never wraps this channel.
   */
  onError?: (data: unknown) => void;
  /** Called on transport errors (network/abort), distinct from `error` events */
  onTransportError?: (err: unknown) => void;
  /** Auto-open when url becomes non-null (default true) */
  enabled?: boolean;
}

interface SSEStatusData {
  step?: string;
  label?: string;
  /** What the pipelines actually send: "active" | "done". */
  state?: string;
  progress?: number;
  status?: string;
  /** `progress` frames report `{done}/{total}` units finished for `step`. */
  done?: number;
  total?: number;
  [key: string]: unknown;
}
interface SSETraceData {
  id?: string;
  kind?: string;
  label?: string;
  durationMs?: number;
  payload?: Record<string, unknown>;
  [key: string]: unknown;
}

export type SSEState = "idle" | "open" | "closed" | "error";

/**
 * EventSource-style streaming over fetch + ReadableStream so the
 * `Authorization: Bearer` header works (native EventSource cannot send it).
 */
export function useSSE(options: UseSSEOptions) {
  const { url, enabled = true } = options;
  const [state, setState] = useState<SSEState>("idle");

  // Keep handlers in a ref so callers can pass inline closures without reconnecting.
  const handlersRef = useRef(options);
  handlersRef.current = options;

  const controllerRef = useRef<AbortController | null>(null);

  const stop = useCallback(() => {
    controllerRef.current?.abort();
    controllerRef.current = null;
  }, []);

  const start = useCallback(async () => {
    if (!url) return;
    stop();
    const controller = new AbortController();
    controllerRef.current = controller;
    setState("open");

    const fullUrl = url.startsWith("http") ? url : `${API_BASE_URL}${url}`;
    const headers: Record<string, string> = { Accept: "text/event-stream" };
    const token = tokenStore.getAccess();
    if (token) headers.Authorization = `Bearer ${token}`;

    try {
      const res = await fetch(fullUrl, { headers, signal: controller.signal });
      if (!res.ok || !res.body) {
        setState("error");
        handlersRef.current.onTransportError?.(
          new Error(`SSE connection failed with status ${res.status}`),
        );
        return;
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      for (;;) {
        const { done, value } = await reader.read();
        // The end of the stream. Whatever is left in the buffer is
        // discarded, and that is the spec's rule rather than an omission:
        // a frame is terminated by the blank line after it, and a server
        // that closed the connection mid-frame left a *partial* frame
        // behind. Dispatching it would append half a token to the answer
        // -- a truncated delta reads as a truncated sentence, which is
        // worse than a turn that ends where it ended.
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        // SSE frames are separated by a blank line.
        const drained = drainFrames(buffer);
        buffer = drained.rest;
        for (const frame of drained.frames) {
          const parsed = parseFrame(frame);
          if (parsed) dispatchEvent(parsed, handlersRef.current);
        }
      }
      setState((s) => (s === "open" ? "closed" : s));
    } catch (err) {
      if (controller.signal.aborted) return; // intentional stop
      setState("error");
      handlersRef.current.onTransportError?.(err);
    }
  }, [url, stop]);

  useEffect(() => {
    if (url && enabled) void start();
    else setState("idle");
    return stop;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [url, enabled]);

  return { state, start, stop };
}

export type SSEHandlers = Pick<
  UseSSEOptions,
  "onStatus" | "onToken" | "onTrace" | "onArtifact" | "onDone" | "onMessage" | "onError"
>;

/** Longest failure cause put on screen; the rest of the frame stays in the logs. */
const MAX_CAUSE_CHARS = 180;

/**
 * The cause a run failed for, or null when the frame carries none.
 *
 * Every publisher on this channel names its key `error` — taskbus.finish writes
 * `{result, error}` with the caught exception text, taskbus.subscribe answers an
 * unknown id with `{error: "task not found"}` — while the relay's own upstream
 * failure is a bare string (`"upstream status 502"`). Reading anything else
 * silently swaps the real reason for a generic sentence on every failure.
 *
 * A cause is `str(e)[:500]` from ai-service and can carry a URL or a stack trace,
 * so only its first line is shown, code-point safely and under `MAX_CAUSE_CHARS`.
 */
export function errorText(data: unknown): string | null {
  const raw =
    typeof data === "string"
      ? data
      : typeof (data as { error?: unknown } | null)?.error === "string"
        ? (data as { error: string }).error
        : null;
  if (!raw) return null;
  const firstLine = raw.split(/\r?\n/)[0].trim();
  if (!firstLine) return null;
  const chars = Array.from(firstLine);
  return chars.length > MAX_CAUSE_CHARS ? `${chars.slice(0, MAX_CAUSE_CHARS - 1).join("")}…` : firstLine;
}

/** A streamed answer delta: ai.stream publishes `{text}`, the name implies `{token}`. */
export function tokenText(data: unknown): string {
  if (typeof data === "string") return data;
  const d = data as { text?: unknown; token?: unknown } | null;
  return String(d?.text ?? d?.token ?? "");
}

/**
 * Route one parsed SSE frame to the matching handler. Exported for testing:
 * this is the transport-agnostic heart of every streaming AI feature.
 */
export function dispatchEvent(evt: SSEEvent, h: SSEHandlers): void {
  switch (evt.event) {
    // `progress` is the same step fold as `status`, just carrying counts instead of a
    // state flip, so it enters through the same door rather than a second handler.
    case "status":
    case "progress":
      h.onStatus?.(evt.data as SSEStatusData);
      break;
    case "token": {
      const text = tokenText(evt.data);
      // An empty delta is not progress: onToken appends it and marks the run as
      // reporting, so a frame we cannot read must not pretend to be one.
      if (text) h.onToken?.(text);
      break;
    }
    case "trace": h.onTrace?.(evt.data as SSETraceData); break;
    case "artifact": h.onArtifact?.(evt.data); break;
    case "done": h.onDone?.(evt.data); break;
    case "message": {
      // DEFECT, pinned by the shape gate (#173): the only producer of a `message` frame is
      // orchestrator.py:277, which publishes `Outcome.to_dict()` -- answer / artifacts / sources /
      // actions / steps / tools_used / run_id. Nothing writes `type`, `token` or a wrapped `data`, so the
      // re-dispatch below can never fire, and its vitest fixtures invented the shape instead of asking
      // the producer. The three signals it claims to forward already arrive as named events. Deleting it
      // needs one live stream check first (R1 is blocked on the owner), so the branch stays and is named.
      const payload = evt.data as { type?: string; data?: unknown; token?: string; content?: string };
      h.onMessage?.(evt.data);
      if (payload && typeof payload === "object") {
        if (payload.type === "token" && (payload.token ?? typeof payload.data === "string")) {
          h.onToken?.(String(payload.token ?? payload.data));
        } else if (payload.type === "status") {
          h.onStatus?.((payload.data ?? payload) as SSEStatusData);
        } else if (payload.type === "trace") {
          h.onTrace?.((payload.data ?? payload) as SSETraceData);
        }
      }
      break;
    }
    case "error": h.onError?.(evt.data); break;
    // taskbus.subscribe sends `ping` every 15s while a run is quiet. It carries no
    // step and no text, so naming it here is the audit trail: every event name the
    // producers publish is either routed above or deliberately dropped.
    case "ping": break;
    default: break;
  }
}

export function findFrameEnd(buffer: string): number {
  const a = buffer.indexOf("\n\n");
  const b = buffer.indexOf("\r\n\r\n");
  if (a === -1 && b === -1) return -1;
  if (a === -1) return b;
  if (b === -1) return a;
  return Math.min(a, b);
}

/**
 * The frames a buffer holds, and the part of it that is not a frame yet.
 *
 * A network read does not land on a frame boundary: a read can carry
 * half a frame, or three and a half. So the buffer accumulates and the
 * frames are taken out of it as they complete, and what is left is what
 * the next read continues.
 *
 * This is the loop the stream reader runs, lifted out of the hook so it
 * can be tested without one -- a hook that needs a renderer is a hook
 * whose body nobody checks, and this is where the frames are cut.
 */
export function drainFrames(buffer: string): { frames: string[]; rest: string } {
  const frames: string[] = [];
  let rest = buffer;
  for (;;) {
    const sep = findFrameEnd(rest);
    if (sep === -1) break;
    frames.push(rest.slice(0, sep));
    rest = rest.slice(sep).replace(/^\r?\n\r?\n/, "");
  }
  return { frames, rest };
}

export function parseFrame(frame: string): SSEEvent | null {
  let event = "message" as SSEEvent["event"];
  const dataLines: string[] = [];
  for (const line of frame.split(/\r?\n/)) {
    if (line.startsWith(":")) continue; // comment / keep-alive
    if (line.startsWith("event:")) event = line.slice(6).trim() as SSEEvent["event"];
    else if (line.startsWith("data:")) dataLines.push(line.slice(5).replace(/^ /, ""));
  }
  if (dataLines.length === 0 && event === "message") return null;
  const raw = dataLines.join("\n");
  let data: unknown = raw;
  if (raw) {
    try {
      data = JSON.parse(raw);
    } catch {
      /* keep as string */
    }
  }
  return { event, data };
}
