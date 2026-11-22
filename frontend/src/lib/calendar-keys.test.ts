import { describe, expect, it } from "vitest";

import { calendarNavFromKey } from "@/lib/calendar-keys";

/**
 * Epic 394 — the calendar's keyboard contract. Three keys are ours; every other
 * key, and every key pressed while typing or holding a modifier, is not.
 */
describe("the calendar keyboard", () => {
  it("walks back and forward on the arrows", () => {
    expect(calendarNavFromKey("ArrowLeft")).toBe("prev");
    expect(calendarNavFromKey("ArrowRight")).toBe("next");
  });

  it("returns to today on either case of T", () => {
    expect(calendarNavFromKey("t")).toBe("today");
    expect(calendarNavFromKey("T")).toBe("today");
  });

  it("leaves typing alone", () => {
    expect(calendarNavFromKey("ArrowLeft", { inField: true })).toBeNull();
    expect(calendarNavFromKey("t", { inField: true })).toBeNull();
  });

  it("leaves shortcuts to the browser and the palette", () => {
    expect(calendarNavFromKey("ArrowLeft", { modifier: true })).toBeNull();
    expect(calendarNavFromKey("t", { modifier: true })).toBeNull();
  });

  it("declines every key it does not own", () => {
    for (const key of ["ArrowUp", "ArrowDown", "Enter", "Escape", "a", "1", " "]) {
      expect(calendarNavFromKey(key)).toBeNull();
    }
  });
});
