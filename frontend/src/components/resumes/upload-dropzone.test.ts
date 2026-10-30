import { describe, expect, it } from "vitest";

import { RESUME_MAX_BYTES } from "@/lib/hooks/actions";
import { lookup } from "@/lib/i18n/locale-context";
import { translations } from "@/lib/i18n/translations";
import { problemMessage } from "./upload-dropzone";

/**
 * The refusal the dropzone shows for a rejected file.
 *
 * The validator answers with a code, and the screen owns the words. Three
 * things are worth pinning here, and the validator's own tests pin none of
 * them: that each code names its own key (a swap turns "too large" into
 * "empty" and no type error notices), that the size in the sentence comes
 * from the cap rather than from a number copied into the copy, and that a
 * Chinese reader no longer reads the English sentence.
 */

const KEYS = ["upload.problemUnsupported", "upload.problemTooLarge", "upload.problemEmpty"];

describe("the upload's refusal", () => {
  it("names the key each reason owns, and the cap's size", () => {
    const calls: { key: string; vars?: Record<string, string | number> }[] = [];
    const t = (key: string, vars?: Record<string, string | number>) => {
      calls.push({ key, vars });
      return key;
    };
    expect(problemMessage(t, "unsupported")).toBe("upload.problemUnsupported");
    expect(problemMessage(t, "too-large")).toBe("upload.problemTooLarge");
    expect(problemMessage(t, "empty")).toBe("upload.problemEmpty");
    expect(calls).toEqual([
      { key: "upload.problemUnsupported", vars: undefined },
      { key: "upload.problemTooLarge", vars: { mb: RESUME_MAX_BYTES / 1024 / 1024 } },
      { key: "upload.problemEmpty", vars: undefined },
    ]);
  });

  it("speaks Chinese to a Chinese reader", () => {
    for (const key of KEYS) {
      const en = lookup(translations.en, key);
      const zh = lookup(translations.zh, key);
      expect(en, `${key} is missing from en`).toBeTruthy();
      expect(zh, `${key} is missing from zh`).toBeTruthy();
      expect(zh, `${key} is the English sentence in zh`).not.toBe(en);
      expect(zh, `${key} has no Chinese in it`).toMatch(/[\u4e00-\u9fff]/);
    }
  });

  it("leaves the size a hole in the accept line, not a copied number", () => {
    for (const locale of ["en", "zh"] as const) {
      const accepted = lookup(translations[locale], "upload.accepted");
      expect(accepted, `upload.accepted is missing from ${locale}`).toBeTruthy();
      expect(accepted, `${locale} accept line does not fill {mb}`).toContain("{mb}");
    }
  });
});