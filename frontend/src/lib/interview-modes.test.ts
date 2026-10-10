import { describe, expect, it } from "vitest";

import { INTERVIEW_MODES } from "@/lib/interview-modes";

/**
 * The picker's own contract: two screens (`/interviews` and the job page) render this list, and the
 * wire value they send is read by the ai-service persona table. What the service accepts is that
 * gate's business; what is tested here is the shape the two menus destructure, so a new entry
 * cannot be added as a bare string and print `system_design` on a candidate's screen.
 */
describe("INTERVIEW_MODES", () => {
  it("gives every entry the three fields the menus read", () => {
    expect(INTERVIEW_MODES.length).toBeGreaterThan(0);
    for (const mode of INTERVIEW_MODES) {
      expect(typeof mode.value, `${JSON.stringify(mode)} has no wire value`).toBe("string");
      expect(typeof mode.label, `${mode.value} has no label`).toBe("string");
      expect(typeof mode.hint, `${mode.value} has no hint`).toBe("string");
      expect(mode.value.length, `${mode.value} has an empty wire value`).toBeGreaterThan(0);
      expect(mode.label.trim(), `${mode.value}'s label is blank`).not.toBe("");
      expect(mode.hint.trim(), `${mode.value}'s hint is blank`).not.toBe("");
    }
  });

  it("sends each mode under one unique wire value", () => {
    const values = INTERVIEW_MODES.map((m) => m.value);
    expect(new Set(values).size, `a duplicate mode value: ${values.join(", ")}`).toBe(values.length);
    for (const value of values) {
      expect(value, `"${value}" is not the lowercase-underscore form the service keys on`)
        .toMatch(/^[a-z][a-z_]*$/);
    }
  });

  it("prints a human label rather than the wire value", () => {
    for (const mode of INTERVIEW_MODES) {
      expect(mode.label, `${mode.value} would print its own wire value on screen`).not.toBe(mode.value);
      expect(mode.label, `"${mode.label}" leaks the wire spelling into the menu`).not.toContain("_");
    }
    const labels = INTERVIEW_MODES.map((m) => m.label);
    expect(new Set(labels).size, `two modes share a label: ${labels.join(", ")}`).toBe(labels.length);
  });
});
