import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

import { ApiError, envelopeError } from "@/lib/api/client";
import { describe as describeError } from "@/lib/hooks/failure";
import { fill } from "@/lib/i18n/locale-context";
import { translations } from "@/lib/i18n/translations";

/**
 * The errors the browser raises itself, and the sentences for them.
 *
 * A toast is raised from an event handler, long after the render that knew
 * the reader's language -- so the sentence a failure shows cannot come from
 * a hook, and it comes from the table instead. The code is what says which
 * sentence: it is the contract ("never rename an emitted code"), and it is
 * the only part of an error that does not change with the wording.
 *
 * These are the failures the *product* has -- the stream that ended early,
 * the upload the reader cancelled, the session that expired. The services'
 * own codes are not in the table: their wording is more specific than one
 * sentence per code can be, and a generic sentence in place of "Start the
 * interview with an opening question first" would be a loss. The server's
 * own words are kept until the vocabulary is fine enough to carry them.
 *
 * The gate holds three things: every code the browser raises has a sentence,
 * the two languages say the same thing about the same codes, and the
 * sentence the reader is shown is the table's -- not the English literal the
 * code was raised with.
 *
 * The codes are read out of the client's own source, not restated here: a
 * gate that keeps its own copy of the vocabulary goes green the moment the
 * two drift apart, which is the whole mistake this gate exists to catch.
 */

const CLIENT = new URL("../api/client.ts", import.meta.url);

/** The codes the browser raises, read out of the client. */
function browserCodes(): string[] {
  const source = readFileSync(CLIENT, "utf-8");
  const found = new Set<string>();
  for (const match of source.matchAll(/new ApiError\(\s*"([A-Z_]+)"/g)) found.add(match[1]);
  return [...found].sort();
}

function table(language: "en" | "zh"): Record<string, string> {
  return (translations[language] as unknown as { errorCodes: Record<string, string> }).errorCodes;
}

describe("the sentences for the errors the browser raises", () => {
  it("has one for every code the browser raises", () => {
    const raised = browserCodes();
    expect(raised.length).toBeGreaterThan(0);
    for (const language of ["en", "zh"] as const) {
      const missing = raised.filter((code) => !table(language)[code]);
      expect(missing, `the ${language} table has no sentence for ${missing.join(", ")}`).toEqual([]);
    }
  });

  it("says the same thing about the same codes in both languages", () => {
    expect(Object.keys(table("zh")).sort()).toEqual(Object.keys(table("en")).sort());
  });

  it("has a sentence that reads as a sentence", () => {
    for (const language of ["en", "zh"] as const) {
      for (const [code, sentence] of Object.entries(table(language))) {
        expect(sentence.trim(), `${language}.errorCodes.${code} is blank`).not.toBe("");
        expect(sentence, `${language}.errorCodes.${code} is the code itself`).not.toBe(code);
      }
    }
  });

  it("shows the reader the table's sentence, not the English the code was raised with", () => {
    // The whole point of the table: the reader sees the sentence in their
    // language. The English literal the code was raised with is the
    // fallback for a build whose table does not have the code yet.
    const sentence = table("en").STREAM_ERROR;
    const shown = describeError(new ApiError("STREAM_ERROR", "The stream failed.", 502), "fallback");
    expect(shown).toBe(sentence);
    expect(shown).not.toBe("The stream failed.");
  });

  it("has a sentence for the code the envelope's fallback raises", () => {
    // A bodyless failure -- a proxy's 502 page, a route that died before the
    // handler -- reaches `envelopeError` with no envelope at all, and the
    // client mints the code itself. The scan above reads `new ApiError("CODE"`
    // literals and cannot see this one, so the code is asked out of the
    // function that raises it rather than out of a shape in the source.
    const statuses = [400, 401, 403, 409, 422, 429, 500, 502, 503];
    for (const language of ["en", "zh"] as const) {
      for (const status of statuses) {
        const err = envelopeError(null, status);
        expect(err.status).toBe(status);
        expect(err.isNotFound, "a 404 is the version sentence's, not this gate's").toBe(false);
        const sentence = table(language)[err.code];
        expect(
          sentence,
          `the ${language} table has no sentence for ${err.code} (status ${status})`,
        ).toBeTruthy();
        expect(sentence, `${language}.errorCodes.${err.code} is the code itself`).not.toBe(err.code);
      }
    }
  });

  it("shows the status in that sentence, not the client's English", () => {
    const shown = describeError(envelopeError(null, 502), "fallback");
    expect(shown).toBe(fill(table("en").HTTP_ERROR, { status: 502 }));
    expect(shown).not.toBe("Request failed with status 502");
    for (const language of ["en", "zh"] as const) {
      const sentence = fill(table(language).HTTP_ERROR, { status: 502 });
      expect(sentence, `${language}.errorCodes.HTTP_ERROR does not carry the status`).toContain("502");
      expect(sentence).not.toContain("{status}");
    }
  });
});
