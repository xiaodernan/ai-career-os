import { describe, expect, it } from "vitest";

import { formatDuration } from "@/components/ai/agent-timeline";

describe("formatDuration", () => {
  it("has nothing to show for a missing duration", () => {
    expect(formatDuration(undefined)).toBeNull();
    expect(formatDuration(null)).toBeNull();
  });

  it("renders under a second in whole milliseconds", () => {
    expect(formatDuration(0)).toBe("0ms");
    expect(formatDuration(1)).toBe("1ms");
    expect(formatDuration(500)).toBe("500ms");
    expect(formatDuration(999)).toBe("999ms");
  });

  it("renders at or above a second with one decimal", () => {
    expect(formatDuration(1000)).toBe("1.0s");
    expect(formatDuration(1500)).toBe("1.5s");
    expect(formatDuration(9999)).toBe("10.0s");
    expect(formatDuration(60_000)).toBe("60.0s");
  });
});
