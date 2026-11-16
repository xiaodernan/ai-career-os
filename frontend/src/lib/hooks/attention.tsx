"use client";

/**
 * Epic 267 — the attention sensor.
 *
 * Records the one or two facts the overseer can actually use: a landing happened, and how
 * long the reader stayed. No clicks, no scroll position, no device fingerprint — if it
 * were anything else it would be a feed, not a sensor. The rows are anonymous aggregates
 * in the admin door; the binary is the browser telling the truth about its own clock.
 */

import * as React from "react";
import { usePathname } from "next/navigation";
import { endpoints } from "@/lib/api/endpoints";
import { API_BASE_URL } from "@/lib/api/endpoints";

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
 * front door's "start free" button is the first caller; the wire fills as readers fill
 * it, and the thirty-day window in /admin answers with the truth.
 */
export function trackAct(path: string, journey: "app" | "public" = "app"): void {
  postTelemetry("act", path, journey);
}

export function AttentionSensor() {
  const pathname = usePathname();

  React.useEffect(() => {
    const start = Date.now();
    postTelemetry("land", pathname, "app");
    return () => {
      postTelemetry("dwell", pathname, "app", String(Date.now() - start));
    };
    // The effect re-fires on every route change: that is the whole point.
  }, [pathname]);

  return null;
}
