import { describe, expect, it } from "vitest";

import { CAPSULE_PROMPT_KEYS, capsulePromptIndex, capsulePromptKey } from "@/lib/capsule-prompts";

/**
 * Epic 396 — the prompt rotates by the calendar day. The same date always gives
 * the same invitation, the next date gives the next one, and stepping past the
 * end wraps rather than falling off.
 */
describe("the capsule prompt", () => {
  const date = new Date(2026, 8, 15, 9, 30);

  it("is stable for one day, whatever the hour", () => {
    expect(capsulePromptKey(date)).toBe(capsulePromptKey(new Date(2026, 8, 15, 23, 59)));
    expect(CAPSULE_PROMPT_KEYS).toContain(capsulePromptKey(date));
  });

  it("moves one prompt a day", () => {
    const index = capsulePromptIndex(date);
    expect(capsulePromptIndex(new Date(2026, 8, 16))).toBe((index + 1) % CAPSULE_PROMPT_KEYS.length);
    expect(capsulePromptKey(new Date(2026, 8, 16))).toBe(
      CAPSULE_PROMPT_KEYS[(index + 1) % CAPSULE_PROMPT_KEYS.length]
    );
  });

  it("steps forward and back without leaving the list", () => {
    const index = capsulePromptIndex(date);
    const size = CAPSULE_PROMPT_KEYS.length;
    expect(capsulePromptIndex(date, size)).toBe(index);
    expect(capsulePromptIndex(date, -1)).toBe((index + size - 1) % size);
    expect(capsulePromptIndex(date, -size - 1)).toBe((index + size - 1) % size);
    for (let offset = -25; offset <= 25; offset += 1) {
      const value = capsulePromptIndex(date, offset);
      expect(value).toBeGreaterThanOrEqual(0);
      expect(value).toBeLessThan(size);
    }
  });
});
