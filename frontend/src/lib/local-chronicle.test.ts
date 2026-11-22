import { describe, expect, it } from "vitest";

import { buildLocalChronicle } from "./local-chronicle";
import type { TimelineEntry } from "@/lib/api/types";

function event(kind: string, at: string, title: string): TimelineEntry {
  return { at, kind, title, refId: title, summary: `${title} summary` };
}

describe("buildLocalChronicle", () => {
  it("writes an honest empty book when there is nothing to tell", () => {
    const book = buildLocalChronicle([]);
    expect(book.empty).toBe(true);
    expect(book.chapters).toEqual([]);
    expect(book.frontier).toHaveLength(6);
  });

  it("opens with the span and the number of regions, then only chapters that have rows", () => {
    const book = buildLocalChronicle(
      [
        event("application", "2026-11-01T10:00:00Z", "Backend Engineer"),
        event("application", "2026-11-08T10:00:00Z", "Platform Engineer"),
        event("interview", "2026-11-10T10:00:00Z", "Systems mock"),
        event("contact", "2026-11-12T10:00:00Z", "Dr. Chen"),
      ],
      { now: new Date("2026-11-22T10:00:00Z").getTime() },
    );
    expect(book.empty).toBe(false);
    expect(book.chapters.map((c) => c.id)).toEqual([
      "opening",
      "applications",
      "interviews",
      "people",
      "now",
    ]);
    expect(book.chapters[0].titleVars).toMatchObject({ days: 12 });
    expect(book.chapters[0].bodyVars).toMatchObject({ total: 4, regions: 3 });
    expect(book.chapters[1].titleVars).toMatchObject({ count: 2 });
    expect(book.chapters[4].bodyVars).toMatchObject({ days: 10 });
  });

  it("puts the newest rows first inside a chapter and caps the lore at three", () => {
    const rows = [1, 2, 3, 4, 5].map((n) =>
      event("application", `2026-11-0${n}T10:00:00Z`, `Role ${n}`),
    );
    const book = buildLocalChronicle(rows);
    const chapter = book.chapters.find((c) => c.id === "applications")!;
    expect(chapter.lore).toHaveLength(3);
    expect(chapter.lore.map((line) => line.vars.title)).toEqual(["Role 5", "Role 4", "Role 3"]);
  });

  it("names the regions the reader has not opened yet", () => {
    const book = buildLocalChronicle([event("note", "2026-11-20T10:00:00Z", "A thought")]);
    expect(book.frontier).toEqual([
      "match",
      "application",
      "interview",
      "contact",
      "resume_version",
    ]);
  });

  it("counts notes and resume versions in one written-record chapter", () => {
    const book = buildLocalChronicle([
      event("note", "2026-11-10T10:00:00Z", "Salary research"),
      event("resume_version", "2026-11-11T10:00:00Z", "Resume v3"),
    ]);
    const chapter = book.chapters.find((c) => c.id === "record")!;
    expect(chapter.titleVars).toMatchObject({ count: 2 });
    expect(chapter.bodyVars).toMatchObject({ notes: 1, versions: 1 });
    expect(chapter.lore).toHaveLength(2);
  });

  it("ignores rows whose timestamp cannot be read", () => {
    const book = buildLocalChronicle([
      event("application", "not-a-date", "Broken"),
      event("note", "2026-11-20T10:00:00Z", "A thought"),
    ]);
    expect(book.chapters[0].bodyVars).toMatchObject({ total: 1 });
  });
});
