import { describe, expect, it } from "vitest";

import {
  TARGET_LOCATIONS_MAX_COUNT,
  TARGET_LOCATIONS_MAX_ITEM,
  TARGET_ROLES_MAX_COUNT,
  TARGET_ROLES_MAX_ITEM,
  splitList,
  targetLocationsIssue,
  targetRolesIssue,
} from "./profile-targets";

describe("splitList", () => {
  it("trims entries, drops blanks, and keeps order", () => {
    expect(splitList(" platform engineer ,, Staff ")).toEqual(["platform engineer", "Staff"]);
  });

  it("reads blank text as an empty list", () => {
    expect(splitList("")).toEqual([]);
    expect(splitList(" , , ")).toEqual([]);
  });
});

describe("targetRolesIssue", () => {
  const full = Array.from({ length: TARGET_ROLES_MAX_COUNT }, (_, i) => `role ${i}`);

  it("accepts a full list whose longest entry sits at the item ceiling", () => {
    expect(
      targetRolesIssue([...full.slice(1), "r".repeat(TARGET_ROLES_MAX_ITEM)]),
    ).toBeUndefined();
  });

  it("refuses a 21st entry", () => {
    expect(targetRolesIssue([...full, "one more"])).toBe(
      `Use at most ${TARGET_ROLES_MAX_COUNT} target roles`,
    );
  });

  it("refuses an over-long role", () => {
    expect(targetRolesIssue(["r".repeat(TARGET_ROLES_MAX_ITEM + 1)])).toBe(
      `Each role can be at most ${TARGET_ROLES_MAX_ITEM} characters`,
    );
  });
});

describe("targetLocationsIssue", () => {
  const full = Array.from({ length: TARGET_LOCATIONS_MAX_COUNT }, (_, i) => `city ${i}`);

  it("accepts a full list whose longest entry sits at the item ceiling", () => {
    expect(
      targetLocationsIssue([...full.slice(1), "l".repeat(TARGET_LOCATIONS_MAX_ITEM)]),
    ).toBeUndefined();
  });

  it("refuses a 21st entry", () => {
    expect(targetLocationsIssue([...full, "one more"])).toBe(
      `Use at most ${TARGET_LOCATIONS_MAX_COUNT} target locations`,
    );
  });

  it("refuses an over-long location", () => {
    expect(targetLocationsIssue(["l".repeat(TARGET_LOCATIONS_MAX_ITEM + 1)])).toBe(
      `Each location can be at most ${TARGET_LOCATIONS_MAX_ITEM} characters`,
    );
  });
});
