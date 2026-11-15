"use client";

/**
 * Epic 225 (reworked in Epic 255) — the reader's wheel dialect, applied app-wide.
 *
 * Mounted once in the app shell. Both dialects force the product's own mapping;
 * the platform is not consulted (the `os` passthrough is gone — it is what made
 * the default feel inverted on the machine it was reported on).
 *
 * standard (default) — the view travels the notch: wheel down → scrollTop
 *                       increases. 往下滑就往下看.
 * natural            — content travels with the gesture: wheel down → scrollTop
 *                       decreases.
 *
 * Reads the stored preference on mount and on every `careeros:wheelDirection`
 * event the settings card dispatches, so the choice applies to this window
 * immediately — no reload. Capture + passive:false so a nested overflow scroller
 * and the window itself both take the same pixels — and the browser's default is
 * suppressed exactly once.
 */

import * as React from "react";
import {
  WHEEL_DIRECTION_EVENT,
  readWheelDirection,
  wheelScrollDelta,
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
  const [mode, setMode] = React.useState<WheelDirection>("standard");

  React.useEffect(() => {
    setMode(readWheelDirection());
    const onChange = (event: Event) => {
      const detail = (event as CustomEvent<WheelDirection>).detail;
      setMode(detail === "natural" ? "natural" : "standard");
    };
    window.addEventListener(WHEEL_DIRECTION_EVENT, onChange);
    return () => window.removeEventListener(WHEEL_DIRECTION_EVENT, onChange);
  }, []);

  React.useEffect(() => {
    if (typeof window === "undefined") return undefined;
    const handler = (event: WheelEvent) => {
      const delta = wheelScrollDelta(event, mode);
      if (delta === null) return; // zoom gesture: the browser owns it
      event.preventDefault();
      const scroller = findScroller(event.target instanceof Element ? event.target : null);
      if (scroller) {
        scroller.scrollTop += delta;
        return;
      }
      // Instant, not smooth: both dialects are forced, and anything else lags.
      window.scrollBy({ top: delta, left: 0, behavior: "instant" as ScrollBehavior });
    };
    document.addEventListener("wheel", handler, { capture: true, passive: false });
    return () => document.removeEventListener("wheel", handler, { capture: true } as AddEventListenerOptions);
  }, [mode]);

  return null;
}
