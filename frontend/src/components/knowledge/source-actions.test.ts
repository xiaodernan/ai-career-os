import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";

import {
  ACCEPTED_EXTENSIONS,
  MAX_DOCUMENT_BYTES,
  SOURCE_KINDS,
  buildDocumentForm,
  validateDocumentFile,
} from "@/components/knowledge/source-actions";

/**
 * Knowledge upload gates. The kind list is a cross-language contract: the backend
 * `validateKind` throws VALIDATION_FAILED on anything outside `KINDS`, so a value the
 * selector can send but the service doesn't name is a 400 the moment it's picked.
 */

const kindsFromJava = () => {
  const java = readFileSync(
    new URL(
      "../../../../backend/src/main/java/com/careeros/knowledge/service/KnowledgeService.java",
      import.meta.url
    ),
    "utf8"
  );
  const declared = java.slice(java.indexOf("KINDS ="), java.indexOf("STATUS_RETIRED"));
  const found = [...declared.matchAll(/"([a-z_]+)"/g)].map((m) => m[1]);
  expect(found.length).toBeGreaterThan(0);
  return found;
};

describe("SOURCE_KINDS", () => {
  it("offers exactly the kinds KnowledgeService.KINDS binds, defaulting to its blank fallback", () => {
    // Same set, no `document` (never in KINDS) and no drift a new value would miss.
    expect([...SOURCE_KINDS].map((k) => k.value).sort()).toEqual([...kindsFromJava()].sort());
    // `uploadDocument` falls back to "note" for a blank kind — the selector's own default.
    expect(SOURCE_KINDS[0].value).toBe("note");
    // Labels stay human-readable next to the snake_case wire values.
    for (const k of SOURCE_KINDS) expect(k.label).toBeTruthy();
  });
});

describe("validateDocumentFile", () => {
  it("accepts an in-cap PDF and rejects the three cases the server would 400", () => {
    expect(validateDocumentFile({ name: "resume.pdf", size: 1024 })).toBeNull();
    expect(validateDocumentFile({ name: "notes.docx", size: 1024 })).toBeNull();
    expect(validateDocumentFile({ name: "notes.txt", size: 1024 })).toBeNull();
    expect(validateDocumentFile({ name: "resume.PDF", size: 1024 })).toBeNull();

    const wrongExt = validateDocumentFile({ name: "resume.exe", size: 1024 });
    expect(wrongExt).toContain(ACCEPTED_EXTENSIONS.join(", "));
    expect(validateDocumentFile({ name: "big.pdf", size: MAX_DOCUMENT_BYTES + 1 })).toMatch(
      /20 MB/
    );
    expect(validateDocumentFile({ name: "empty.txt", size: 0 })).toMatch(/empty/);
  });
});

describe("buildDocumentForm", () => {
  it("sends file + kind as parts and only sends a title the user typed", () => {
    const file = new File(["hi"], "cv.pdf", { type: "application/pdf" });
    const withTitle = buildDocumentForm(file, "  My CV  ", "resume");
    expect(withTitle.get("file")).toBe(file);
    expect(withTitle.get("kind")).toBe("resume");
    expect(withTitle.get("title")).toBe("My CV");

    const blank = buildDocumentForm(file, "   ", "note");
    expect(blank.get("title")).toBeNull();
    expect(blank.get("kind")).toBe("note");
  });
});
