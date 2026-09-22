import { describe, expect, it } from "vitest";

import { APPLICATION_STAGES, isTerminal, STAGE_ORDER, stageMeta } from "./pipeline";

describe("stageMeta", () => {
  it("returns known stage metadata", () => {
    const offer = stageMeta("offer");
    expect(offer.label).toBe("Offer");
    expect(offer.badgeVariant).toBe("success");
  });
  it("falls back gracefully for unknown status", () => {
    const unknown = stageMeta("ghost");
    expect(unknown.badgeVariant).toBe("outline");
    expect(unknown.label).toBe("ghost");
    expect(stageMeta("").label).toBe("Unknown");
  });
});

describe("STAGE_ORDER", () => {
  it("mirrors the declared board order", () => {
    expect(STAGE_ORDER).toEqual(APPLICATION_STAGES.map((s) => s.value));
    expect(STAGE_ORDER[0]).toBe("saved");
    expect(STAGE_ORDER[STAGE_ORDER.length - 1]).toBe("rejected");
  });
});

describe("isTerminal", () => {
  it("treats only offer and rejected as terminal", () => {
    expect(isTerminal("offer")).toBe(true);
    expect(isTerminal("rejected")).toBe(true);
    expect(isTerminal("interview")).toBe(false);
  });
});
