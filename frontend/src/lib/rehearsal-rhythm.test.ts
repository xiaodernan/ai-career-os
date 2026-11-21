import { describe, expect, it } from "vitest";

import { RHYTHM_BANDS, rehearsalRhythm } from "./rehearsal-rhythm";

/**
 * 374: how long it has been since the reader last rehearsed.
 *
 * The bands are the product's own (stated, not derived), and the rule is honest
 * about every degenerate input: an empty ledger, an unparseable date and a clock in
 * the future all answer something true rather than a number.
 */

const NOW = new Date("2026-11-22T12:00:00Z");

describe("rehearsalRhythm", () => {
  it("counts the days since the last rehearsal", () => {
    const out = rehearsalRhythm({
      sessions: [{ at: "2026-11-19T12:00:00Z" }, { at: "2026-11-01T12:00:00Z" }],
      now: NOW,
    });
    expect(out.daysSince).toBe(3);
    expect(out.lastAt).toBe("2026-11-19T12:00:00Z");
    expect(out.band).toBe("fresh");
  });

  it("takes the newest, not the first it is handed", () => {
    const out = rehearsalRhythm({
      sessions: [{ at: "2026-10-01T12:00:00Z" }, { at: "2026-11-20T12:00:00Z" }],
      now: NOW,
    });
    expect(out.daysSince).toBe(2);
  });

  it("bands the habit: fresh, warm, stale", () => {
    const at = (days: number) => new Date(NOW.getTime() - days * 86_400_000).toISOString();
    expect(rehearsalRhythm({ sessions: [{ at: at(0) }], now: NOW }).band).toBe("fresh");
    expect(rehearsalRhythm({ sessions: [{ at: at(RHYTHM_BANDS.fresh) }], now: NOW }).band).toBe("fresh");
    expect(rehearsalRhythm({ sessions: [{ at: at(RHYTHM_BANDS.fresh + 1) }], now: NOW }).band).toBe("warm");
    expect(rehearsalRhythm({ sessions: [{ at: at(RHYTHM_BANDS.warm) }], now: NOW }).band).toBe("warm");
    expect(rehearsalRhythm({ sessions: [{ at: at(RHYTHM_BANDS.warm + 1) }], now: NOW }).band).toBe("stale");
  });

  it("answers 'none' for a reader who has never rehearsed", () => {
    // Not a criticism: they have not started. The sentence is different, and so is
    // the door.
    const out = rehearsalRhythm({ sessions: [], now: NOW });
    expect(out).toEqual({ daysSince: null, lastAt: null, band: "none" });
  });

  it("ignores a row whose date it cannot read", () => {
    const out = rehearsalRhythm({
      sessions: [{ at: "not-a-date" }, { at: "2026-11-21T12:00:00Z" }],
      now: NOW,
    });
    expect(out.daysSince).toBe(1);
    expect(out.lastAt).toBe("2026-11-21T12:00:00Z");
  });

  it("never reports a negative gap for a clock ahead of the row", () => {
    const out = rehearsalRhythm({ sessions: [{ at: "2026-12-01T12:00:00Z" }], now: NOW });
    expect(out.daysSince).toBe(0);
    expect(out.band).toBe("fresh");
  });
});
