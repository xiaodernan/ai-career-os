/**
 * The wheel, the reader's way (Epic 225).
 *
 * Nothing in this product ever inverted a wheel — `git log
 * -S"addEventListener('wheel'" -- frontend/src` is empty, and no stylesheet
 * flips a scroller. What the reader actually meets is the disagreement
 * between macOS and Windows about what "scroll direction: natural" means,
 * and this module is the answer: one setting, honored app-wide, never
 * applied silently.
 *
 * The pure layer takes structural nodes (no DOM types), so the math and the
 * scroll walk are unit-tested in the node runner; the DOM layer is the
 * capture-phase handler in the layout.
 *
 * Sign discipline: `reversedScrollDelta` is what the reader asked for when
 * the preference is "reverse the wheel" — the NEGATIVE of the browser's
 * default — and `scrollTop += delta` applies it. Positive scrollTop keeps
 * meaning "further down the page".
 */

export type WheelDirection = "os" | "reverse";

const STORAGE_KEY = "careeros.wheelDirection";
const EVENT = "careeros:wheelDirection";

export const WHEEL_DIRECTION_EVENT = EVENT;
export const WHEEL_DIRECTION_KEY = STORAGE_KEY;

const LINE_PX = 16;
const PAGE_PX = 40;

type StorageLike = Pick<Storage, "getItem" | "setItem">;

const defaultStorage = (): StorageLike | null =>
  typeof window === "undefined" ? null : window.localStorage;

/** The stored preference, clamped to the two the product knows. */
export function readWheelDirection(storage: StorageLike | null = defaultStorage()): WheelDirection {
  if (!storage) return "os";
  try {
    return storage.getItem(STORAGE_KEY) === "reverse" ? "reverse" : "os";
  } catch {
    return "os";
  }
}

/** Persist and tell this window about the flip (same-tab views update without a reload). */
export function writeWheelDirection(
  direction: WheelDirection,
  storage: StorageLike | null = defaultStorage(),
): void {
  if (!storage) return;
  try {
    storage.setItem(STORAGE_KEY, direction);
  } catch {
    // best effort — the visible setting still flips for this session via the event
  }
  try {
    window.dispatchEvent(new CustomEvent<WheelDirection>(EVENT, { detail: direction }));
  } catch {
    // no window (tests, server) — the event is decoration; the storage write is the truth
  }
}

/** The pixels the browser would apply to a scroll position, sign included. */
export function normalizeWheelDeltaY(e: { deltaY: number; deltaMode?: number }): number {
  if (!Number.isFinite(e.deltaY) || e.deltaY === 0) return 0;
  const mode = e.deltaMode ?? 0;
  if (mode === 1) return e.deltaY * LINE_PX; // DOM_DELTA_LINE
  if (mode === 2) return e.deltaY * PAGE_PX; // DOM_DELTA_PAGE
  return e.deltaY; // DOM_DELTA_PIXEL
}

/**
 * The delta the reader asked for when the preference is "reverse the wheel" —
 * the negative of the browser's default. `null` when the browser should keep
 * the event untouched: ctrl/⌘+wheel is the zoom gesture every browser owns.
 */
export function reversedScrollDelta(e: {
  deltaY: number;
  deltaMode?: number;
  ctrlKey?: boolean;
  metaKey?: boolean;
}): number | null {
  if (e.ctrlKey || e.metaKey) return null;
  const natural = normalizeWheelDeltaY(e);
  return natural === 0 ? null : -natural;
}

/** One node of the scroll walk. Structural — the DOM never enters the test. */
export interface ScrollNode {
  overflowY: string;
  scrollHeight: number;
  clientHeight: number;
  scrollTop: number;
  parentElement: ScrollNode | null;
}

/** The nearest ancestor (or self) that vertically overflows and accepts scroll. */
export function nearestVerticalScroller(start: ScrollNode | null): ScrollNode | null {
  let node = start;
  while (node) {
    const overflow = node.overflowY;
    if (
      (overflow === "auto" || overflow === "scroll" || overflow === "overlay") &&
      node.scrollHeight > node.clientHeight + 1
    ) {
      return node;
    }
    node = node.parentElement;
  }
  return null;
}
