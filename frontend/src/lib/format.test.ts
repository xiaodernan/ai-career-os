import { describe, expect, it } from "vitest";

import {
  formatDuration,
  formatSalary,
  formatUsd,
  initialsOf,
  pluralize,
  relativeTime,
  slugify,
  titleCase,
} from "./format";

describe("formatSalary", () => {
  it("prefers explicit text when present", () => {
    expect(formatSalary(1, 2, "USD", "Negotiable")).toBe("Negotiable");
  });
  it("renders a USD compact range with an en dash", () => {
    expect(formatSalary(40000, 60000, "USD")).toBe("$40k–$60k");
  });
  it("renders CNY in 万", () => {
    expect(formatSalary(300000, 450000, "CNY")).toBe("30万–45万");
  });
  it("renders open-ended bounds", () => {
    expect(formatSalary(50000, null, "USD")).toBe("$50k+");
    expect(formatSalary(null, 20000, "USD")).toBe("up to $20k");
  });
  it("returns null with no numbers and no text", () => {
    expect(formatSalary(null, null, null, null)).toBeNull();
  });
});

describe("formatUsd", () => {
  it("uses 4 decimals below a cent", () => {
    expect(formatUsd(0.005)).toBe("$0.0050");
    expect(formatUsd(1.5)).toBe("$1.50");
  });
  it("shows an em dash for missing values", () => {
    expect(formatUsd(null)).toBe("—");
  });
});

describe("formatDuration", () => {
  it("scales units", () => {
    expect(formatDuration(500)).toBe("500ms");
    expect(formatDuration(1500)).toBe("1.5s");
    expect(formatDuration(65_000)).toBe("1m 5s");
    expect(formatDuration(null)).toBe("");
  });
});

describe("pluralize", () => {
  it("handles one, many and custom plural", () => {
    expect(pluralize(1, "job")).toBe("1 job");
    expect(pluralize(3, "job")).toBe("3 jobs");
    expect(pluralize(2, "box", "boxes")).toBe("2 boxes");
  });
});

describe("titleCase", () => {
  it("splits separators and uppercases words", () => {
    expect(titleCase("hello_world-x")).toBe("Hello World X");
    expect(titleCase("")).toBe("");
  });
});

describe("initialsOf", () => {
  it("takes up to two leading letters", () => {
    expect(initialsOf("john", "doe")).toBe("JD");
    expect(initialsOf("ada@example.com")).toBe("AE");
    expect(initialsOf()).toBe("?");
  });
});

describe("slugify", () => {
  it("kebab-cases and guards the empty string", () => {
    expect(slugify("Hello World!")).toBe("hello-world");
    expect(slugify("   ")).toBe("document");
  });
});

describe("relativeTime", () => {
  const ago = (ms: number) => new Date(Date.now() - ms).toISOString();
  it("buckets into minutes/hours/days", () => {
    expect(relativeTime(ago(1_000))).toBe("just now");
    expect(relativeTime(ago(5 * 60_000))).toBe("5m ago");
    expect(relativeTime(ago(3 * 3_600_000))).toBe("3h ago");
    expect(relativeTime(ago(5 * 86_400_000))).toBe("5d ago");
    expect(relativeTime(null)).toBe("");
  });
});
