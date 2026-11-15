import { describe, expect, it } from "vitest";
import {
  WHEEL_DIRECTION_EVENT,
  nearestVerticalScroller,
  normalizeWheelDeltaY,
  readWheelDirection,
  wheelScrollDelta,
  writeWheelDirection,
  type ScrollNode,
} from "./wheel-direction";

function memoryStorage(seed: Record<string, string> = {}) {
  const map = new Map<string, string>(Object.entries(seed));
  return {
    getItem: (k: string) => map.get(k) ?? null,
    setItem: (k: string, v: string) => void map.set(k, v),
  };
}

function node(partial: Partial<ScrollNode> = {}): ScrollNode {
  const base: ScrollNode = {
    overflowY: "visible",
    scrollHeight: 100,
    clientHeight: 100,
    scrollTop: 0,
    parentElement: null,
  };
  return { ...base, ...partial, parentElement: partial.parentElement ?? null };
}

describe("readWheelDirection / writeWheelDirection", () => {
  it("defaults to standard, migrating Epic 225's `os` onto the forced dialect", () => {
    expect(readWheelDirection(memoryStorage())).toBe("standard");
    expect(readWheelDirection(memoryStorage({ "careeros.wheelDirection": "os" }))).toBe("standard");
    expect(readWheelDirection(memoryStorage({ "careeros.wheelDirection": "reverse" }))).toBe("natural");
    expect(readWheelDirection(memoryStorage({ "careeros.wheelDirection": "natural" }))).toBe("natural");
    expect(readWheelDirection(memoryStorage({ "careeros.wheelDirection": "bogus" }))).toBe("standard");
  });

  it("falls back to standard when storage throws", () => {
    expect(readWheelDirection(null)).toBe("standard");
    const broken = {
      getItem(): string | null {
        throw new Error("locked");
      },
      setItem(): void {
        throw new Error("locked");
      },
    };
    expect(readWheelDirection(broken)).toBe("standard");
    expect(() => writeWheelDirection("natural", broken)).not.toThrow();
  });

  it("round-trips the two dialects and only ever emits one of the two values", () => {
    const storage = memoryStorage();
    writeWheelDirection("natural", storage);
    expect(storage.getItem("careeros.wheelDirection")).toBe("natural");
    writeWheelDirection("standard", storage);
    expect(storage.getItem("careeros.wheelDirection")).toBe("standard");
  });
});

describe("normalizeWheelDeltaY", () => {
  it("passes pixel deltas through unchanged", () => {
    expect(normalizeWheelDeltaY({ deltaY: 120, deltaMode: 0 })).toBe(120);
    expect(normalizeWheelDeltaY({ deltaY: -3, deltaMode: 0 })).toBe(-3);
  });

  it("scales lines by 16 and pages by 40", () => {
    expect(normalizeWheelDeltaY({ deltaY: 3, deltaMode: 1 })).toBe(48);
    expect(normalizeWheelDeltaY({ deltaY: 1, deltaMode: 2 })).toBe(40);
  });

  it("treats non-finite and zero deltas as zero", () => {
    expect(normalizeWheelDeltaY({ deltaY: 0, deltaMode: 0 })).toBe(0);
    expect(normalizeWheelDeltaY({ deltaY: Number.NaN, deltaMode: 0 })).toBe(0);
    expect(normalizeWheelDeltaY({ deltaY: Number.POSITIVE_INFINITY, deltaMode: 0 })).toBe(0);
  });
});

describe("wheelScrollDelta", () => {
  it("standard: the view travels the notch (positive goes down)", () => {
    expect(wheelScrollDelta({ deltaY: 120, deltaMode: 0 }, "standard")).toBe(120);
    expect(wheelScrollDelta({ deltaY: -3, deltaMode: 1 }, "standard")).toBe(-48);
    expect(wheelScrollDelta({ deltaY: 1, deltaMode: 2 }, "standard")).toBe(40);
  });

  it("natural: content travels with the gesture (positive goes up)", () => {
    expect(wheelScrollDelta({ deltaY: 120, deltaMode: 0 }, "natural")).toBe(-120);
    expect(wheelScrollDelta({ deltaY: -3, deltaMode: 1 }, "natural")).toBe(48);
    expect(wheelScrollDelta({ deltaY: 1, deltaMode: 2 }, "natural")).toBe(-40);
  });

  it("defaults to standard when no dialect is named", () => {
    expect(wheelScrollDelta({ deltaY: 120, deltaMode: 0 })).toBe(120);
  });

  it("leaves the zoom gesture alone in both dialects", () => {
    expect(wheelScrollDelta({ deltaY: 120, deltaMode: 0, ctrlKey: true }, "standard")).toBeNull();
    expect(wheelScrollDelta({ deltaY: 120, deltaMode: 0, metaKey: true }, "standard")).toBeNull();
    expect(wheelScrollDelta({ deltaY: 120, deltaMode: 0, ctrlKey: true }, "natural")).toBeNull();
  });

  it("is null for a zero delta", () => {
    expect(wheelScrollDelta({ deltaY: 0, deltaMode: 0 }, "standard")).toBeNull();
    expect(wheelScrollDelta({ deltaY: 0, deltaMode: 0 }, "natural")).toBeNull();
  });
});

describe("nearestVerticalScroller", () => {
  it("returns the inner scroller, skipping non-overflow ancestors", () => {
    const window: ScrollNode = node({ overflowY: "auto", scrollHeight: 800, clientHeight: 600 });
    const inner: ScrollNode = node({ overflowY: "scroll", scrollHeight: 400, clientHeight: 300, parentElement: window });
    const row: ScrollNode = node({ overflowY: "visible", parentElement: inner });
    expect(nearestVerticalScroller(row)).toBe(inner);
    expect(nearestVerticalScroller(inner)).toBe(inner);
  });

  it("accepts 'overlay' as a scrolling overflow and rejects non-overflowing boxes", () => {
    const overlay: ScrollNode = node({ overflowY: "overlay", scrollHeight: 900, clientHeight: 600 });
    const noScroll: ScrollNode = node({ overflowY: "auto", scrollHeight: 100, clientHeight: 100 });
    const row: ScrollNode = node({ overflowY: "visible", parentElement: overlay });
    expect(nearestVerticalScroller(row)).toBe(overlay);
    expect(nearestVerticalScroller(noScroll)).toBeNull();
  });

  it("returns null when no scroller exists", () => {
    expect(nearestVerticalScroller(null)).toBeNull();
    expect(nearestVerticalScroller(node())).toBeNull();
  });
});

describe("the event contract", () => {
  it("names the same event the setting page dispatches", () => {
    expect(WHEEL_DIRECTION_EVENT).toBe("careeros:wheelDirection");
  });
});
