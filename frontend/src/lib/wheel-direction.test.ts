import { describe, expect, it } from "vitest";
import {
  WHEEL_DIRECTION_EVENT,
  nearestVerticalScroller,
  normalizeWheelDeltaY,
  readWheelDirection,
  reversedScrollDelta,
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
  it("defaults to the OS when nothing is stored", () => {
    expect(readWheelDirection(memoryStorage())).toBe("os");
    expect(readWheelDirection(memoryStorage({ "careeros.wheelDirection": "reverse" }))).toBe("reverse");
    expect(readWheelDirection(memoryStorage({ "careeros.wheelDirection": "bogus" }))).toBe("os");
  });

  it("falls back to the OS when storage throws", () => {
    expect(readWheelDirection(null)).toBe("os");
    const broken = {
      getItem(): string | null {
        throw new Error("locked");
      },
      setItem(): void {
        throw new Error("locked");
      },
    };
    expect(readWheelDirection(broken)).toBe("os");
    expect(() => writeWheelDirection("reverse", broken)).not.toThrow();
  });

  it("round-trips 'reverse' and only ever emits one of the two values", () => {
    const storage = memoryStorage();
    writeWheelDirection("reverse", storage);
    expect(storage.getItem("careeros.wheelDirection")).toBe("reverse");
    writeWheelDirection("os", storage);
    expect(storage.getItem("careeros.wheelDirection")).toBe("os");
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

describe("reversedScrollDelta", () => {
  it("negates the delta the browser would apply", () => {
    expect(reversedScrollDelta({ deltaY: 120, deltaMode: 0 })).toBe(-120);
    expect(reversedScrollDelta({ deltaY: -3, deltaMode: 1 })).toBe(48);
  });

  it("leaves the zoom gesture alone", () => {
    expect(reversedScrollDelta({ deltaY: 120, deltaMode: 0, ctrlKey: true })).toBeNull();
    expect(reversedScrollDelta({ deltaY: 120, deltaMode: 0, metaKey: true })).toBeNull();
  });

  it("is null for a zero delta", () => {
    expect(reversedScrollDelta({ deltaY: 0, deltaMode: 0 })).toBeNull();
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
