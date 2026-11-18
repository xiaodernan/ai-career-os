/**
 * The wheel, the reader's way.
 *
 * The product always applies its own direction now, on every platform: the
 * reader's complaint was that the old `os` passthrough left "wheel down →
 * look down" to whatever the desktop did to the signal, and on their machine
 * it arrived inverted. There are two dialects, both forced app-wide:
 *
 *   standard — the view travels the notch (positive deltaY → scrollTop
 *              increases). "往下滑就往下看". This is the default.
 *   natural  — content travels with the gesture (positive deltaY → scrollTop
 *              decreases). For the reader whose fingers expect pull-to-follow.
 *
 * The storage key and event are unchanged from Epic 225; a stored value is
 * migrated on read: "os" → "standard" (the ask), "reverse" → "natural". A
 * bogus value is standard. The pure layer takes structural nodes (no DOM
 * types), so the math and the scroll walk are unit-tested in the node runner;
 * the DOM layer is the capture-phase handler in the layout.
 *
 * Sign discipline: `wheelScrollDelta(e, direction)` is the signed step the
 * reader asked for; applying it is `scrollTop += step`. Positive scrollTop
 * keeps meaning "further down the page".
 */

export type WheelDirection = "standard" | "natural";

const STORAGE_KEY = "careeros.wheelDirection";
const STORAGE_KEY_V2 = "careeros.wheelDirection.v2";
const EVENT = "careeros:wheelDirection";

export const WHEEL_DIRECTION_EVENT = EVENT;
export const WHEEL_DIRECTION_KEY = STORAGE_KEY_V2;

const LINE_PX = 16;
const PAGE_PX = 40;

type StorageLike = Pick<Storage, "getItem" | "setItem">;

const defaultStorage = (): StorageLike | null =>
  typeof window === "undefined" ? null : window.localStorage;

/** The stored preference, clamped to the two the product knows.
 *
 * Epic 255 still honored Epic 225's legacy values: `reverse` mapped onto `natural`,
 * which left the exact reader who asked for "down is down" staring at an inverted
 * wheel forever. This is the one-time reset: any value stored under the legacy key
 * is dropped and the corrected default (standard) is written to the v2 key, so a
 * machine that arrived feeling backwards lands forwards after one load. From then
 * on the v2 key rules — an explicit natural stays natural, a picked standard stays
 * standard, and the legacy key is never read again.
 */
export function readWheelDirection(storage: StorageLike | null = defaultStorage()): WheelDirection {
  if (!storage) return "standard";
  try {
    const v2 = storage.getItem(STORAGE_KEY_V2);
    if (v2 === "natural" || v2 === "standard") return v2;
    if (storage.getItem(STORAGE_KEY) !== null) {
      try {
        storage.setItem(STORAGE_KEY_V2, "standard");
      } catch {
        /* best effort — the reader still gets the corrected default this load */
      }
    }
    return "standard";
  } catch {
    return "standard";
  }
}

/** Persist and tell this window about the flip (same-tab views update without a reload). */
export function writeWheelDirection(
  direction: WheelDirection,
  storage: StorageLike | null = defaultStorage(),
): void {
  if (!storage) return;
  try {
    storage.setItem(STORAGE_KEY_V2, direction);
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
 * The signed step for the reader's dialect, or null for the browser to keep the
 * event untouched: ctrl/⌘+wheel is the zoom gesture every browser owns.
 *
 * Standard applies the browser's own direction (positive goes down); natural
 * negates it. Both are forced; neither consults the platform.
 */
export function wheelScrollDelta(
  e: {
    deltaY: number;
    deltaMode?: number;
    ctrlKey?: boolean;
    metaKey?: boolean;
  },
  direction: WheelDirection = "standard",
): number | null {
  if (e.ctrlKey || e.metaKey) return null;
  const natural = normalizeWheelDeltaY(e);
  if (natural === 0) return null;
  return direction === "natural" ? -natural : natural;
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
