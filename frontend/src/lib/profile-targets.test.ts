import { describe, expect, it } from "vitest";

import { fill, lookup } from "./i18n/locale-context";
import { translations } from "./i18n/translations";
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
    expect(targetRolesIssue([...full, "one more"])).toEqual({
      key: "profile.issues.tooManyRoles",
      params: { max: TARGET_ROLES_MAX_COUNT },
    });
  });

  it("refuses an over-long role", () => {
    expect(targetRolesIssue(["r".repeat(TARGET_ROLES_MAX_ITEM + 1)])).toEqual({
      key: "profile.issues.roleTooLong",
      params: { max: TARGET_ROLES_MAX_ITEM },
    });
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
    expect(targetLocationsIssue([...full, "one more"])).toEqual({
      key: "profile.issues.tooManyLocations",
      params: { max: TARGET_LOCATIONS_MAX_COUNT },
    });
  });

  it("refuses an over-long location", () => {
    expect(targetLocationsIssue(["l".repeat(TARGET_LOCATIONS_MAX_ITEM + 1)])).toEqual({
      key: "profile.issues.locationTooLong",
      params: { max: TARGET_LOCATIONS_MAX_ITEM },
    });
  });
});

describe("the issue keys", () => {
  it("have a sentence in both languages, with the ceiling filled in", () => {
    const en = (key: string, vars?: Record<string, string | number>) => {
      const value = lookup(translations.en, key);
      if (value === undefined) throw new Error("the English table has no " + key);
      return fill(value, vars);
    };
    const issues = [
      targetRolesIssue(Array.from({ length: TARGET_ROLES_MAX_COUNT + 1 }, () => "r")),
      targetRolesIssue(["r".repeat(TARGET_ROLES_MAX_ITEM + 1)]),
      targetLocationsIssue(Array.from({ length: TARGET_LOCATIONS_MAX_COUNT + 1 }, () => "l")),
      targetLocationsIssue(["l".repeat(TARGET_LOCATIONS_MAX_ITEM + 1)]),
    ];
    for (const issue of issues) {
      expect(issue).toBeDefined();
      if (issue === undefined) continue;
      const sentence = en(issue.key, issue.params);
      expect(sentence).not.toMatch(/{w+}/);
      expect(lookup(translations.zh, issue.key)).toBeTypeOf("string");
    }
  });
});
