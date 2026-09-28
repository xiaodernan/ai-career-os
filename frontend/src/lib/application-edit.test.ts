import { describe, expect, it } from "vitest";

import { fromReminderInput, reminderPatch, toReminderInput } from "./application-edit";

/** Built from local components so the expectations hold in any timezone CI runs in. */
const LOCAL = new Date(2026, 8, 30, 9, 0);

describe("toReminderInput", () => {
  it("renders an instant as the local wall time the picker shows", () => {
    expect(toReminderInput(LOCAL.toISOString())).toBe("2026-09-30T09:00");
  });
  it("pads single-digit months, days, hours and minutes", () => {
    expect(toReminderInput(new Date(2026, 0, 5, 7, 4).toISOString())).toBe("2026-01-05T07:04");
  });
  it("has nothing to render for an absent or unparseable reminder", () => {
    expect(toReminderInput(null)).toBe("");
    expect(toReminderInput(undefined)).toBe("");
    expect(toReminderInput("not a date")).toBe("");
  });
});

describe("fromReminderInput", () => {
  it("reads the picker's value as local time, not UTC", () => {
    expect(fromReminderInput("2026-09-30T09:00")).toBe(LOCAL.toISOString());
  });
  it("treats an empty or unparseable field as no reminder", () => {
    expect(fromReminderInput("")).toBeNull();
    expect(fromReminderInput("   ")).toBeNull();
    expect(fromReminderInput("nonsense")).toBeNull();
  });
});

describe("reminderPatch", () => {
  it("says nothing when the picker was not touched", () => {
    expect(reminderPatch(LOCAL.toISOString(), toReminderInput(LOCAL.toISOString()))).toEqual({});
  });
  it("says nothing when a row with no reminder is left empty", () => {
    expect(reminderPatch(null, "")).toEqual({});
  });
  it("sends the instant when a reminder is set or moved", () => {
    expect(reminderPatch(null, "2026-09-30T09:00")).toEqual({ reminderAt: LOCAL.toISOString() });
  });
  it("clears instead of sending an empty instant when the picker is emptied", () => {
    // A null component means "leave it alone" on the PATCH body, so an emptied picker has to
    // travel as the explicit flag or the reminder would be impossible to remove.
    expect(reminderPatch(LOCAL.toISOString(), "")).toEqual({ clearReminderAt: true });
  });
  it("ignores the distance between two spellings of the same instant", () => {
    const sameMoment = new Date(LOCAL.getTime()).toISOString();
    expect(reminderPatch(sameMoment, toReminderInput(LOCAL.toISOString()))).toEqual({});
  });
});
