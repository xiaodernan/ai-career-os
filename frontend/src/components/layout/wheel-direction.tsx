"use client";

/**
 * Epic 225 — the reader's wheel direction, applied app-wide.
 *
 * Mounted once in the app shell. Reads the stored preference on mount and on
 * every `careeros:wheelDirection` event the settings card dispatches, so the
 * choice applies to this window immediately — no reload. When the preference
 * is "os" (the default), this component attaches nothing and every wheel is
 * the browser's own.
 *
 * Reversal is captured at the document with capture + passive:false, so a
 * nested overflow scroller and the window itself both take the same inverted
 * pixels — and the browser's default is suppressed exactly once.
 */

import * as React from "react";
import {
  WHEEL_DIRECTION_EVENT,
  readWheelDirection,
  reversedScrollDelta,
  type WheelDirection,
} from "@/lib/wheel-direction";

/** Walk real elements up from `start`; the first that overflows wins. */
function findScroller(start: Element | null): HTMLElement | null {
  let el = start;
  while (el) {
    if (el instanceof HTMLElement) {
      const style = window.getComputedStyle(el);
      const overflowY = style.overflowY;
      if (
        (overflowY === "auto" || overflowY === "scroll" || overflowY === "overlay") &&
        el.scrollHeight > el.clientHeight + 1
      ) {
        return el;
      }
    }
    el = el.parentElement;
  }
  return null;
}

export function WheelDirection() {
  const [mode, setMode] = React.useState<WheelDirection>("os");

  React.useEffect(() => {
    setMode(readWheelDirection());
    const onChange = (event: Event) => {
      const detail = (event as CustomEvent<WheelDirection>).detail;
      setMode(detail === "reverse" ? "reverse" : "os");
    };
    window.addEventListener(WHEEL_DIRECTION_EVENT, onChange);
    return () => window.removeEventListener(WHEEL_DIRECTION_EVENT, onChange);
  }, []);

  React.useEffect(() => {
    if (mode !== "reverse" || typeof window === "undefined") return undefined;
    const handler = (event: WheelEvent) => {
      const delta = reversedScrollDelta(event);
      if (delta === null) return; // zoom gesture: the browser owns it
      event.preventDefault();
      const scroller = findScroller(event.target instanceof Element ? event.target : null);
      if (scroller) {
        scroller.scrollTop += delta;
        return;
      }
      // Instant, not smooth: the reader asked for a reversed wheel, the platform
      // honours one with an immediate step, and anything else feels like lag.
      window.scrollBy({ top: delta, left: 0, behavior: "instant" as ScrollBehavior });
    };
    // capture + passive:false so the handler runs before the browser's own
    // default and can supersede it once per wheel tick.
    document.addEventListener("wheel", handler, { capture: true, passive: false });
    return () => document.removeEventListener("wheel", handler, { capture: true } as AddEventListenerOptions);
  }, [mode]);

  return null;
}
