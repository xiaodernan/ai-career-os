import { describe, expect, it } from "vitest";

import { funnelReading } from "./admin-funnel";

describe("funnelReading", () => {
  it("names the steepest single-stage loss and its share", () => {
    const out = funnelReading(
      [
        { id: "registered", readers: 100 },
        { id: "uploaded", readers: 50 },
        { id: "applied", readers: 10 },
        { id: "interviewed", readers: 9 },
      ],
      40,
    );
    expect(out.bottleneckStageId).toBe("applied");
    expect(out.bottleneckPercent).toBe(20);
    expect(out.matchedSharePercent).toBe(40);
  });

  it("keeps the earlier flat collapse honestly (interviewed 0 is out of the set when prev is zero)", () => {
    const out = funnelReading(
      [
        { id: "registered", readers: 100 },
        { id: "uploaded", readers: 1 },
        { id: "applied", readers: 0 },
        { id: "interviewed", readers: 0 },
      ],
      0,
    );
    // applied's 0% from the single uploader is the steepest honest ratio; prev=0 in the next step is skipped
    expect(out.bottleneckStageId).toBe("applied");
    expect(out.bottleneckPercent).toBe(0);
    expect(out.matchedSharePercent).toBe(0);
  });

  it("reads a degenerate line without inventing a bottleneck", () => {
    const out = funnelReading([{ id: "registered", readers: 0 }], undefined);
    expect(out.bottleneckStageId).toBeNull();
    expect(out.bottleneckPercent).toBeNull();
    expect(out.matchedSharePercent).toBeNull();
  });

  it("matches this install's real shape (23 / 40 / 57 / 6)", () => {
    const out = funnelReading(
      [
        { id: "registered", readers: 6655 },
        { id: "uploaded", readers: 1543 },
        { id: "applied", readers: 610 },
        { id: "interviewed", readers: 345 },
        { id: "offered", readers: 20 },
      ],
      264,
    );
    expect(out.bottleneckStageId).toBe("offered");
    expect(out.bottleneckPercent).toBe(6);
    expect(out.matchedSharePercent).toBe(4);
  });
});
