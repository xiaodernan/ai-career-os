import { describe, expect, it } from "vitest";

import { reminderApplicationId } from "./notification-reminder";

const ID = "3f2b8c1e-6a4d-4f9b-8e2c-1d5a7b9c0e3f";

describe("reminderApplicationId", () => {
  it("reads the application out of a reminder episode's key", () => {
    expect(reminderApplicationId(`reminder:${ID}:1761600000`)).toBe(ID);
  });

  it("accepts an upper-case UUID, because the id is the id", () => {
    expect(reminderApplicationId(`reminder:${ID.toUpperCase()}:1761600000`)).toBe(
      ID.toUpperCase()
    );
  });

  it("answers only for reminders: a stale row has nothing to snooze", () => {
    expect(reminderApplicationId(`stale:${ID}:1761500000`)).toBeNull();
    expect(reminderApplicationId(`ingestion:run-1`)).toBeNull();
  });

  it("refuses a key whose id is not an id", () => {
    expect(reminderApplicationId("reminder:app-1:1761600000")).toBeNull();
    expect(reminderApplicationId("reminder::1761600000")).toBeNull();
  });

  it("refuses a reminder without its episode, because that key was never one the inbox made", () => {
    expect(reminderApplicationId(`reminder:${ID}:`)).toBeNull();
    expect(reminderApplicationId(`reminder:${ID}:not-an-epoch`)).toBeNull();
  });

  it("refuses keys that are not the shape at all", () => {
    expect(reminderApplicationId("")).toBeNull();
    expect(reminderApplicationId(`reminder:${ID}:1761600000:extra`)).toBeNull();
  });
});
