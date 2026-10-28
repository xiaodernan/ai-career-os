import { describe, expect, it } from "vitest";

import {
  DEPTH_BANDS,
  depthBand,
  depthLevel,
  weightBand,
  formatDate,
  formatDateOnly,
  formatDateTime,
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
import { fill, lookup } from "./i18n/locale-context";
import { translations } from "./i18n/translations";

describe("formatSalary", () => {
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
  it("returns null when both bounds are missing", () => {
    expect(formatSalary(null, null, null)).toBeNull();
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

describe("depthLevel / depthBand", () => {
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

  it("names each rung with a band token, and never a rung that has no name", () => {
    expect(depthBand(0)).toBe("warmup");
    expect(depthBand(0.6)).toBe("solid");
    expect(depthBand(5)).toBe("expert");
    expect(depthBand(9)).toBe("expert");
    expect(depthBand(2)).toBe("standard");
    expect(new Set(DEPTH_BANDS).size).toBe(DEPTH_BANDS.length);
  });
});

describe("the depth bands", () => {
  it("has a word for every band in both languages", () => {
    // The meter asks for the key at paint time (`interviews.depthBands.${band}`),
    // so no scan can see whether the table holds it. A missing one would render
    // the dot-path on the badge, in every language at once.
    for (const band of DEPTH_BANDS) {
      for (const [locale, table] of Object.entries(translations)) {
        const key = `interviews.depthBands.${band}`;
        expect(lookup(table, key), `${locale} has no ${key}`).toBeTypeOf("string");
      }
    }
  });

  it("renders the report's depth badge in the reader's language", () => {
    // The badge read `reached depth 3 / 5 · Solid` under every locale: the
    // sentence was two JSX text nodes and the last word was a table of five
    // English strings in format.ts. Compose it the way the page does.
    const compose = (locale: "en" | "zh") => {
      const table = translations[locale];
      const word = lookup(table, `interviews.depthBands.${depthBand(0.6)}`);
      expect(word, `${locale} has no word for solid`).toBeTypeOf("string");
      const sentence = lookup(table, "interviews.report.depthReached");
      expect(sentence, `${locale} has no depthReached`).toBeTypeOf("string");
      return fill(sentence as string, { level: 3, band: word as string });
    };
    expect(compose("zh")).toBe("达到深度 3 / 5 · 扎实");
    expect(compose("en")).toBe("Reached depth 3 / 5 · Solid");
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

describe("formatDate", () => {
  // Built from local components, so the rendered day is the same in every time zone.
  const local = (y: number, m: number, d: number, h = 0, min = 0) =>
    new Date(y, m - 1, d, h, min).toISOString();

  it("draws the date in the reader's language, not the machine's", () => {
    // `undefined` used to mean "whatever the browser's locale is": on a zh-CN machine an English
    // reader saw "2026年10月28日" inside English sentences, and on an en-US machine a Chinese
    // reader saw "Oct 28, 2026" inside Chinese ones.
    expect(formatDate(local(2026, 10, 28), "en")).toBe("Oct 28, 2026");
    expect(formatDate(local(2026, 10, 28), "zh")).toBe("2026年10月28日");
  });

  it("keeps the empty and unparseable answers", () => {
    expect(formatDate(null, "zh")).toBe("");
    expect(formatDate("not a date", "en")).toBe("not a date");
  });
});

describe("formatDateOnly", () => {
  it("keeps the calendar date the backend sent, in the reader's language", () => {
    // "2026-10-26" parsed as a moment is UTC midnight; a reader in Los Angeles would have
    // been shown Oct 25. A week starts on a date, so the date is what is drawn, whatever
    // zone the machine is in.
    expect(formatDateOnly("2026-10-26", "en")).toBe("Oct 26, 2026");
    expect(formatDateOnly("2026-10-26", "zh")).toBe("2026年10月26日");
  });

  it("keeps the empty answer and falls back for a moment-shaped value", () => {
    expect(formatDateOnly("", "en")).toBe("");
    expect(formatDateOnly("2026-10-26T08:00:00Z", "en")).toBe(formatDate("2026-10-26T08:00:00Z", "en"));
  });
});

describe("formatDateTime", () => {
  const local = (y: number, m: number, d: number, h = 0, min = 0) =>
    new Date(y, m - 1, d, h, min).toISOString();

  it("draws the day and the clock in the reader's language", () => {
    expect(formatDateTime(local(2026, 10, 28, 14, 5), "en")).toMatch(/^Oct 28, 02:05\sPM$/);
    expect(formatDateTime(local(2026, 10, 28, 14, 5), "zh")).toBe("10月28日 14:05");
  });

  it("keeps the empty and unparseable answers", () => {
    expect(formatDateTime(undefined, "en")).toBe("");
    expect(formatDateTime("not a date", "zh")).toBe("not a date");
  });
});

describe("relativeTime", () => {
  const ago = (ms: number) => new Date(Date.now() - ms).toISOString();
  const ahead = (ms: number) => new Date(Date.now() + ms).toISOString();

  it("keeps the compact English buckets it shipped", () => {
    expect(relativeTime(ago(1_000), "en")).toBe("now");
    expect(relativeTime(ago(5 * 60_000), "en")).toBe("5m ago");
    expect(relativeTime(ago(3 * 3_600_000), "en")).toBe("3h ago");
    expect(relativeTime(ago(5 * 86_400_000), "en")).toBe("5d ago");
    expect(relativeTime(ago(40 * 86_400_000), "en")).toBe("1mo ago");
    expect(relativeTime(ago(400 * 86_400_000), "en")).toBe("1y ago");
    expect(relativeTime(null, "en")).toBe("");
  });

  it("speaks the reader's language when the reader chose Chinese", () => {
    // The stamp sits inside translated sentences -- "收藏于 {date}", "最近一步：{when}" -- so an
    // English unit read as "收藏于 5d ago": one language per screen, on every list that dates a row.
    expect(relativeTime(ago(1_000), "zh")).toBe("现在");
    expect(relativeTime(ago(5 * 60_000), "zh")).toBe("5分钟前");
    expect(relativeTime(ago(3 * 3_600_000), "zh")).toBe("3小时前");
    expect(relativeTime(ago(5 * 86_400_000), "zh")).toBe("5天前");
    expect(relativeTime(ago(40 * 86_400_000), "zh")).toBe("1个月前");
    expect(relativeTime(ago(400 * 86_400_000), "zh")).toBe("1年前");
  });

  it("reads a future timestamp forward, not as a negative age", () => {
    // reminderAt is ahead of now by definition. The old subtract-and-divide kept the sign in the
    // divisor and printed "-1440m ago" on a reminder set for tomorrow.
    expect(relativeTime(ahead(3 * 3_600_000), "en")).toBe("in 3h");
    expect(relativeTime(ahead(3 * 3_600_000), "zh")).toBe("3小时后");
  });

  it("hands back an unparseable value rather than inventing an age", () => {
    expect(relativeTime("not a date", "zh")).toBe("not a date");
  });
});

describe("weightBand", () => {
  it("maps the two bands and the middle", () => {
    expect(weightBand(1.0)).toBe("high");
    expect(weightBand(0.9)).toBe("high");
    expect(weightBand(0.85)).toBe("high"); // boundary inclusive
    expect(weightBand(0.6)).toBe("normal");
    expect(weightBand(0.5)).toBe("normal");
    expect(weightBand(0.36)).toBe("normal");
    expect(weightBand(0.35)).toBe("low"); // boundary inclusive
    expect(weightBand(0.3)).toBe("low");
    expect(weightBand(0)).toBe("low");
  });

  it("treats a non-number as normal rather than high or low", () => {
    expect(weightBand(Number.NaN)).toBe("normal");
  });
});
