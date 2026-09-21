"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { API_BASE_URL } from "@/lib/api/endpoints";
import { tokenStore } from "@/lib/api/token-store";
import type { SSEEventName } from "@/lib/api/types";

export interface SSEEvent {
  event: SSEEventName | "message";
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
  onError?: (data: { code?: string; message?: string; details?: unknown }) => void;
  /** Called on transport errors (network/abort), distinct from `error` events */
  onTransportError?: (err: unknown) => void;
  /** Auto-open when url becomes non-null (default true) */
  enabled?: boolean;
}

interface SSEStatusData {
  step?: string;
  label?: string;
  progress?: number;
  status?: string;
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
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        // SSE frames are separated by a blank line.
        let sep: number;
        while ((sep = findFrameEnd(buffer)) !== -1) {
          const frame = buffer.slice(0, sep);
          buffer = buffer.slice(sep).replace(/^\r?\n\r?\n/, "");
          const parsed = parseFrame(frame);
          if (parsed) dispatch(parsed);
        }
      }
      setState((s) => (s === "open" ? "closed" : s));
    } catch (err) {
      if (controller.signal.aborted) return; // intentional stop
      setState("error");
      handlersRef.current.onTransportError?.(err);
    }

    function dispatch(evt: SSEEvent) {
      const h = handlersRef.current;
      switch (evt.event) {
        case "status": h.onStatus?.(evt.data as SSEStatusData); break;
        case "token":
          h.onToken?.(
            typeof evt.data === "string" ? evt.data : String((evt.data as { token?: unknown }).token ?? ""),
          );
          break;
        case "trace": h.onTrace?.(evt.data as SSETraceData); break;
        case "artifact": h.onArtifact?.(evt.data); break;
        case "done": h.onDone?.(evt.data); break;
        case "message": {
          // The relay wraps payloads in `message` frames — unwrap the common
          // {type, data} shape so callers still see status/token/trace events.
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
        case "error": h.onError?.(evt.data as { code?: string; message?: string; details?: unknown }); break;
        default: break;
      }
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

function findFrameEnd(buffer: string): number {
  const a = buffer.indexOf("\n\n");
  const b = buffer.indexOf("\r\n\r\n");
  if (a === -1 && b === -1) return -1;
  if (a === -1) return b;
  if (b === -1) return a;
  return Math.min(a, b);
}

function parseFrame(frame: string): SSEEvent | null {
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
