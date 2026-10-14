import { describe, expect, it } from "vitest";

import { RESUME_MAX_BYTES, validateResumeFile } from "@/lib/hooks/actions";

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
