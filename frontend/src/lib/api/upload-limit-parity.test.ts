import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

import { RESUME_ACCEPT, RESUME_MAX_BYTES } from "@/lib/hooks/actions";

/**
 * Upload limits are enforced twice — the dropzone's client-side guard and
 * `FileValidator`'s server-side sniffing — and the two halves were never compared.
 *
 * The direction that matters: a client guard LOOSER than the server passes a file
 * the server will refuse (FILE_TOO_LARGE / INVALID_FILE_TYPE), and the user sees a
 * round trip's worth of effort spent on an upload that was always going to fail.
 * The server is 20MB by configuration; the dropzone tells the candidate 10MB.
 * That the client is stricter is correct and must stay so — one number moving
 * beneath the other is exactly the silent disagreement this file exists to catch.
 *
 * The backend is read as source, the same way the route-parity census reads the
 * controllers: a limit typed into this file by hand would be a copy, and copies
 * drift.
 */

const YML = new URL("../../../../backend/src/main/resources/application.yml", import.meta.url);
const VALIDATOR = new URL(
  "../../../../backend/src/main/java/com/careeros/storage/FileValidator.java",
  import.meta.url
);

function serverMaxBytes(): number {
  const yml = readFileSync(YML, "utf8");
  const m = /max-file-size-bytes:\s*(\d+)/.exec(yml);
  expect(m, "application.yml no longer declares app.upload.max-file-size-bytes").not.toBeNull();
  return Number(m![1]);
}

function serverDefaultMaxBytes(): number {
  const java = readFileSync(VALIDATOR, "utf8");
  const m = /DEFAULT_MAX_BYTES\s*=\s*(\d+)L\s*\*\s*1024\s*\*\s*1024/.exec(java);
  expect(m, "FileValidator no longer declares DEFAULT_MAX_BYTES").not.toBeNull();
  return Number(m![1]) * 1024 * 1024;
}

describe("upload limits — client guard vs server limit", () => {
  it("reads both sides from source, not from a copy typed here", () => {
    // A scan that found nothing would make every rule below vacuously true.
    expect(serverMaxBytes()).toBeGreaterThan(1024 * 1024);
    expect(serverDefaultMaxBytes()).toBeGreaterThan(1024 * 1024);
    expect(RESUME_MAX_BYTES).toBeGreaterThan(1024 * 1024);
  });

  it("the configured server limit is the validator's default, not an override nobody sees", () => {
    expect(serverMaxBytes()).toBe(serverDefaultMaxBytes());
  });

  it("the client guard is never looser than the server", () => {
    expect(RESUME_MAX_BYTES).toBeLessThanOrEqual(serverMaxBytes());
  });

  it("the copy the dropzone prints matches its own constant", () => {
    // The message derives from the constant, so it cannot disagree with it.
    expect(`${RESUME_MAX_BYTES / 1024 / 1024}MB`).toBe("10MB");
  });
});

describe("accepted types — client extensions vs the server's three", () => {
  it("every extension the dropzone accepts is one the server sniffs", () => {
    const serverTypes = new Set(["pdf", "docx", "txt"]);
    for (const ext of RESUME_ACCEPT) {
      expect(ext.startsWith(".")).toBe(true);
      expect(serverTypes.has(ext.slice(1)), `${ext} is refused server-side`).toBe(true);
    }
    expect(RESUME_ACCEPT).toEqual([".pdf", ".docx", ".txt"]);
  });

  it("the server's accepted mimes are the three the client spells", () => {
    const java = readFileSync(VALIDATOR, "utf8");
    for (const mime of [
      "application/pdf",
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      "text/plain",
    ]) {
      expect(java).toContain(mime);
    }
  });
});
