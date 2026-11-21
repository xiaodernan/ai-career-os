"use client";

/**
 * Epic 267 — the attention sensor, extended (Block IX) with the two behaviours the
 * operator actually asked to watch: leaving almost as soon as you arrived, and clicking
 * around without settling.
 *
 * Records only what the overseer can use: a landing, how long the reader stayed, an act,
 * a bounce (left too fast), or an aimless hop (moved on without reading). No clicks on
 * content, no scroll position, no device fingerprint — a sensor, not a feed. The rows
 * are anonymous aggregates in the admin door; the binary is the browser telling the
 * truth about its own clock.
 */

import * as React from "react";
import { usePathname } from "next/navigation";
import { endpoints } from "@/lib/api/endpoints";
import { API_BASE_URL } from "@/lib/api/endpoints";

/** Below this the reader did not really read the page — a bounce, not a dwell. */
const BOUNCE_MS = 4_000;
/** Two different rooms inside this window is a lost reader, not a journey. */
const AIMLESS_HOP_MS = 6_000;

/** The anonymous signal's own post, fire-and-forget: one fetch, one catch, no state held anywhere. */
function postTelemetry(event: string, path: string, journey: "app" | "public", value?: string): void {
  try {
    fetch(`${API_BASE_URL}${endpoints.telemetry.attention}`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      // the tab may already be closing, which is exactly the case this carries
      keepalive: true,
      body: JSON.stringify({ journey, path, event, value }),
    }).catch(() => undefined);
  } catch {
    /* telemetry is fire-and-forget by design; a failed signal loses nothing */
  }
}

/**
 * Epic 283 — the third verb, now written: one anonymous act, fired the moment a reader
 * means it. Same posture as the sensor: no value, no identity, no fingerprint. The
 * front door's "start free" button is the first caller.
 */
export function trackAct(path: string, journey: "app" | "public" = "app"): void {
  postTelemetry("act", path, journey);
}

/**
 * A room was left. If the reader spent less than BOUNCE_MS here, record a bounce with
 * the time-on-page; otherwise record the honest dwell. Called both on route change and
 * on tab hide/close, guarded so the two never double-count the same visit.
 */
export function leaveRoom(path: string, start: number, journey: "app" | "public", closed: boolean, reported: { done: boolean }): void {
  if (reported.done) return;
  reported.done = true;
  const ms = Math.max(0, Date.now() - start);
  postTelemetry(ms < BOUNCE_MS ? "bounce" : "dwell", path, journey, String(ms));
  // A tab that closes is not a navigation: nothing else to say.
  void closed;
}

export function AttentionSensor() {
  const pathname = usePathname();
  const history = React.useRef<Array<{ path: string; at: number }>>([]);

  React.useEffect(() => {
    const start = Date.now();
    const reported = { done: false };
    postTelemetry("land", pathname, "app");

    // Did the reader arrive somewhere else moments ago? Rapid room-hopping with no
    // settled read is the "don't know where to go, clicking around" behaviour.
    const now = start;
    const recent = history.current.filter((h) => now - h.at <= AIMLESS_HOP_MS);
    if (recent.some((h) => h.path !== pathname)) {
      postTelemetry("aimless", pathname, "app");
    }
    history.current = [...recent.slice(-4), { path: pathname, at: now }];

    const onHide = () => {
      if (document.visibilityState === "hidden") {
        leaveRoom(pathname, start, "app", true, reported);
      }
    };
    document.addEventListener("visibilitychange", onHide);
    window.addEventListener("pagehide", onHide);
    return () => {
      document.removeEventListener("visibilitychange", onHide);
      window.removeEventListener("pagehide", onHide);
      leaveRoom(pathname, start, "app", false, reported);
    };
    // The effect re-fires on every route change: that is the whole point.
  }, [pathname]);

  return null;
}
