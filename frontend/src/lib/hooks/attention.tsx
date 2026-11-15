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

export function AttentionSensor() {
  const pathname = usePathname();

  React.useEffect(() => {
    const start = Date.now();

    const send = (event: string, value?: string) => {
      try {
        fetch(`${API_BASE_URL}${endpoints.telemetry.attention}`, {
          method: "POST",
          headers: { "content-type": "application/json" },
          // the tab may already be closing, which is exactly the case this carries
          keepalive: true,
          body: JSON.stringify({ journey: "app", path: pathname, event, value }),
        }).catch(() => undefined);
      } catch {
        /* telemetry is fire-and-forget by design; a failed signal loses nothing */
      }
    };

    send("land");
    return () => {
      send("dwell", String(Date.now() - start));
    };
    // The effect re-fires on every route change: that is the whole point.
  }, [pathname]);

  return null;
}
