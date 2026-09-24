import { describe, expect, it } from "vitest";

import {
  depthLabel,
  depthLevel,
  formatDuration,
  formatSalary,
  formatUsd,
  initialsOf,
  pluralize,
  relativeTime,
  seniorityLabel,
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
  it("treats CNY input as 元/年, not 万/年", () => {
    // Binding unit contract: the API and DB store CNY as base-unit-per-year (元/年),
    // so 380000 must read as 38万. Legacy rows that stored 万/年 (30 meaning 30万)
    // rendered as "0万"; they are repaired by V2__normalize_salary_units.sql and this
    // test pins the convention so the formatter itself is never "fixed" to match them.
    expect(formatSalary(380000, 680000, "CNY")).toBe("38万–68万");
    expect(formatSalary(70000, 120000, "CNY")).toBe("7万–12万");
    expect(formatSalary(30, 45, "CNY")).toBe("0万–0万");
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

describe("depthLevel / depthLabel", () => {
  it("projects the pipeline's 0–1 difficulty onto the 1–5 ladder it is drawn as", () => {
    // interview_sessions.difficulty in the live DB sits in [0.5, 0.65]; decide_next
    // clamps to [0.1, 0.95]. Printing that float on a badge reading "depth N / 5" made
    // every session look like depth 0 with an empty meter.
    expect(depthLevel(0.1)).toBe(1);
    expect(depthLevel(0.6)).toBe(3);
    expect(depthLevel(0.95)).toBe(5);
  });

  it("leaves an already-laddered value alone and stays inside 1–5", () => {
    expect(depthLevel(3)).toBe(3);
    expect(depthLevel(5)).toBe(5);
    // A fraction of 1.0 is the top of the producer scale, not "Warm-up".
    expect(depthLevel(1)).toBe(5);
    // The meter draws five pips, so it must never be asked for 0 or 7.
    expect(depthLevel(0)).toBe(1);
    expect(depthLevel(7)).toBe(5);
  });

  it("names each rung, and never a rung that has no name", () => {
    expect(depthLabel(0)).toBe("Warm-up");
    expect(depthLabel(0.6)).toBe("Solid");
    expect(depthLabel(5)).toBe("Expert");
    expect(depthLabel(9)).toBe("Expert");
    expect(depthLabel(2)).toBe("Standard");
  });
});

describe("seniorityLabel", () => {
  it("turns the stored years into the chip text the job header draws", () => {
    // Live DB distribution of jobs.experience_years today: 0(4) 2(5) 3(20) 4(9) 5(3),
    // null(5) — so 41 of 46 job pages had a value and showed no chip at all.
    expect(seniorityLabel(3)).toBe("3+ years experience");
    expect(seniorityLabel(1)).toBe("1+ year experience");
    expect(seniorityLabel(5)).toBe("5+ years experience");
  });

  it("keeps 0 as a real answer and null as not stated", () => {
    // "Entry level" and "no chip" are different facts; printing "0+ years" would be
    // neither, and faking 0 for a missing value would claim the posting said something.
    expect(seniorityLabel(0)).toBe("Entry level");
    expect(seniorityLabel(null)).toBeUndefined();
    expect(seniorityLabel(undefined)).toBeUndefined();
    expect(seniorityLabel(Number.NaN)).toBeUndefined();
  });

  it("refuses a number that can only be a parse artifact", () => {
    // The JD importer stores whatever the model answered for experienceYears verbatim,
    // and a bare year in the posting text ("founded 2024") is the classic misread.
    expect(seniorityLabel(2024)).toBeUndefined();
    expect(seniorityLabel(30)).toBe("30+ years experience");
    expect(seniorityLabel(-1)).toBeUndefined();
    expect(seniorityLabel(3.7)).toBe("3+ years experience");
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
