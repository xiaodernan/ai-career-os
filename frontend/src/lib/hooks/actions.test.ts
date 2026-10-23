import { describe, expect, it } from "vitest";

import type { Application } from "@/lib/api/types";
import { RESUME_MAX_BYTES, optimisticApplicationRow, validateResumeFile } from "@/lib/hooks/actions";

/**
 * The client-side size/mime guard, so an unsupported file never hits the network.
 * The backend validates again (FileValidatorTest), but this is the half the
 * browser shows: an extension OR a mime is enough, because a file dragged out
 * of some managers arrives with no `file.type` at all — rejecting on mime alone
 * would refuse perfectly good PDFs — and "looks empty" is a distinct answer from
 * "too big", because a 0-byte file is a failed drag, not an oversized resume.
 */

function file(name: string, type: string, size: number): File {
  return { name, type, size } as File;
}

describe("validateResumeFile", () => {
  it("accepts any of the three extensions, case-insensitively", () => {
    for (const name of ["a.pdf", "a.docx", "a.txt", "A.PDF", "resume final.DOCX"]) {
      expect(validateResumeFile(file(name, "", 1024))).toBeNull();
    }
  });

  it("accepts on mime even when the name says otherwise", () => {
    // An extension-less temp upload with a real mime is still a resume.
    expect(validateResumeFile(file("tmpblob", "application/pdf", 1024))).toBeNull();
    expect(validateResumeFile(file("tmpblob", "text/plain", 1024))).toBeNull();
    expect(validateResumeFile(file("tmpblob", "application/msword", 1024))).toBeNull();
  });

  it("refuses a file that is neither supported-extension nor supported-mime", () => {
    expect(validateResumeFile(file("resume.exe", "application/x-msdownload", 1024)))
        .toBe("Only PDF, DOCX or TXT files are supported.");
    expect(validateResumeFile(file("resume.zip", "", 1024)))
        .toBe("Only PDF, DOCX or TXT files are supported.");
  });

  it("distinguishes an oversized file from an empty one", () => {
    expect(validateResumeFile(file("a.pdf", "application/pdf", RESUME_MAX_BYTES + 1)))
        .toBe("File is larger than 10MB.");
    expect(validateResumeFile(file("a.pdf", "application/pdf", RESUME_MAX_BYTES)))
        .toBeNull();
    expect(validateResumeFile(file("a.pdf", "application/pdf", 0)))
        .toBe("That file looks empty.");
  });

  it("checks the type before the size, so the message names the real problem", () => {
    // An oversized .exe is first rejected as the wrong type of file.
    expect(validateResumeFile(file("a.exe", "", RESUME_MAX_BYTES * 2)))
        .toBe("Only PDF, DOCX or TXT files are supported.");
  });
});

/**
 * The optimistic row the board draws between the click and the refetch.
 *
 * The PATCH body is a command vocabulary and the cached row is an answer, so the merge that puts
 * one onto the other has to translate the one command that names a field rather than a value:
 * `clearReminderAt`. `reminderAt: null` cannot travel to the server (a null component there means
 * "leave it alone"), so the removal only reaches the screen through this row — and `kanban.tsx`
 * reads it twice, for the chip and for `overdue`.
 */

function row(over: Partial<Application> = {}): Application {
  return {
    id: "app-1",
    title: "Backend engineer",
    status: "interview",
    note: "recruiter call booked",
    reminderAt: "2026-11-01T09:00:00Z",
    position: 3,
    ...over,
  } as Application;
}

describe("optimisticApplicationRow", () => {
  it("drops the instant the command clears, so the card stops drawing a reminder that is gone", () => {
    expect(optimisticApplicationRow(row(), { clearReminderAt: true }).reminderAt).toBeNull();
  });

  it("writes the instant the command sets", () => {
    const next = "2026-12-24T10:30:00Z";
    expect(optimisticApplicationRow(row(), { reminderAt: next }).reminderAt).toBe(next);
  });

  it("leaves the instant alone for a command that says nothing about reminders", () => {
    // The board's drag and the note's save both land here; neither may blank the reminder.
    expect(optimisticApplicationRow(row(), { status: "offer" }).reminderAt).toBe("2026-11-01T09:00:00Z");
    expect(optimisticApplicationRow(row(), { note: "moved" }).reminderAt).toBe("2026-11-01T09:00:00Z");
    expect(optimisticApplicationRow(row(), { position: 7 }).position).toBe(7);
  });

  it("keeps the row's own answer names, which no command carries", () => {
    const merged = optimisticApplicationRow(row(), { clearReminderAt: true });
    expect(merged.id).toBe("app-1");
    expect(merged.title).toBe("Backend engineer");
    expect(merged.note).toBe("recruiter call booked");
  });

  it("lets the clear win when one command carries both spellings", () => {
    // The dialog never sends both, but the merge order is the whole mechanism: the nulling pair is
    // spread last, so a contradictory body reads as removed rather than as the older instant.
    const merged = optimisticApplicationRow(row(), { reminderAt: "2027-01-01T00:00:00Z", clearReminderAt: true });
    expect(merged.reminderAt).toBeNull();
  });
});
