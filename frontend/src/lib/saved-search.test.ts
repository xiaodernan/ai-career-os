import { describe, expect, it } from "vitest";

import { criteriaFromFilters, filtersFromCriteria, suggestedName } from "./saved-search";

/**
 * The two translations a saved search needs: the URL's flat filters to the
 * stored criteria, and back. The pair is a round trip — a search saved from
 * the board and then re-applied has to ask the same question it was saved
 * from, or the row is a name for a different search.
 */

describe("criteriaFromFilters", () => {
  it("keeps the board's question and drops the presentation", () => {
    expect(
      criteriaFromFilters({
        q: " backend ",
        skills: " Java, , Spring, Java ",
        location: " Hangzhou ",
        company: " ",
        remote: true,
        min_salary: 30000,
        max_salary: 0,
      })
    ).toEqual({
      q: "backend",
      location: "Hangzhou",
      remote: true,
      minSalary: 30000,
      maxSalary: 0,
      skills: ["Java", "Spring"],
    });
  });

  it("treats a switched-off remote toggle as no criterion", () => {
    expect(criteriaFromFilters({ remote: false, q: "backend" })).toEqual({ q: "backend" });
  });

  it("has nothing to store when the board is browsing", () => {
    expect(criteriaFromFilters({})).toBeUndefined();
    expect(criteriaFromFilters({ q: " ", skills: " , ", remote: false })).toBeUndefined();
  });
});

describe("filtersFromCriteria", () => {
  it("sets every filter field, so applying replaces rather than merges", () => {
    expect(filtersFromCriteria({ q: "backend", skills: ["Java", "Spring"] })).toEqual({
      q: "backend",
      skills: "Java,Spring",
      location: "",
      company: "",
      remote: undefined,
      min_salary: undefined,
      max_salary: undefined,
    });
  });

  it("round-trips through criteriaFromFilters", () => {
    const criteria = {
      q: "backend",
      location: "Hangzhou",
      remote: true,
      minSalary: 30000,
      maxSalary: 60000,
      skills: ["Java"],
    };
    expect(criteriaFromFilters(filtersFromCriteria(criteria))).toEqual(criteria);
  });

  it("keeps a salary ceiling with no floor", () => {
    expect(criteriaFromFilters(filtersFromCriteria({ maxSalary: 60000 }))).toEqual({
      maxSalary: 60000,
    });
  });
});

describe("suggestedName", () => {
  const t = (key: string) => {
    expect(key).toBe("savedSearches.remoteName");
    return "Remote roles";
  };

  it("names the most specific criterion first", () => {
    expect(suggestedName({ q: "backend", location: "Hangzhou" }, t)).toBe("backend");
    expect(suggestedName({ location: "Hangzhou", skills: ["Java"] }, t)).toBe("Hangzhou");
    expect(suggestedName({ company: "Acme", remote: true }, t)).toBe("Acme");
    expect(suggestedName({ skills: ["Java", "Spring"] }, t)).toBe("Java, Spring");
  });

  it("asks the table only for a remote-only search", () => {
    expect(suggestedName({ remote: true }, t)).toBe("Remote roles");
  });

  it("suggests nothing for a search that stores nothing", () => {
    expect(suggestedName({}, t)).toBe("");
  });
});
