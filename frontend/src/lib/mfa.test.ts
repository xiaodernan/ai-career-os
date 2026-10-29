import { describe, expect, it } from "vitest";

import {
  activateCodeIssue,
  proofCodeIssue,
  proofPasswordIssue,
  recoveryCodesText,
  spacedSecret,
} from "@/lib/mfa";

/**
 * The second factor's arithmetic (roadmap 36.4).
 *
 * The screen around these functions is the expensive part to test and the part a
 * future redesign may rewrite; the three decisions it makes before rendering are
 * the ones that would break quietly. A seed grouped by threes still looks like a
 * key and imports as the wrong secret; a copy-all that trims or quotes a code
 * hands the reader a string the server refuses; a local six-digit rule on the
 * proof field refuses the printed code that is the whole point of the sheet.
 */

describe("the seed the enrollment answers", () => {
  it("groups base32 in fours, the way authenticators print it", () => {
    expect(spacedSecret("JBSWY3DPEHPK3PXP")).toBe("JBSW Y3DP EHPK 3PXP");
  });

  it("forgets the whitespace a paste brings, then regroups", () => {
    expect(spacedSecret(" JBSW Y3DP EH PK3PXP\n")).toBe("JBSW Y3DP EHPK 3PXP");
  });

  it("leaves a short or empty seed alone rather than inventing groups", () => {
    expect(spacedSecret("ABCD")).toBe("ABCD");
    expect(spacedSecret("")).toBe("");
  });
});

describe("the recovery codes on their way out of the screen", () => {
  it("is one code per line, in printed order, with nothing added", () => {
    const codes = ["AAAA-BBBB", "CCCC-DDDD", "EEEE-FFFF"];
    expect(recoveryCodesText(codes)).toBe("AAAA-BBBB\nCCCC-DDDD\nEEEE-FFFF");
  });

  it("is empty for no codes rather than a stray newline", () => {
    expect(recoveryCodesText([])).toBe("");
  });
});

describe("the code fields' local rules", () => {
  it("activation wants exactly six digits, because that is the record's pattern", () => {
    expect(activateCodeIssue("123456")).toBeUndefined();
    expect(activateCodeIssue(" 123456 ")).toBeUndefined();
    expect(activateCodeIssue("")).toEqual({ key: "security.issues.codeRequired" });
    expect(activateCodeIssue("12345")).toEqual({ key: "security.issues.codeSixDigits" });
    expect(activateCodeIssue("1234567")).toEqual({ key: "security.issues.codeSixDigits" });
    expect(activateCodeIssue("12 34 56")).toEqual({ key: "security.issues.codeSixDigits" });
    expect(activateCodeIssue("ABCDEF")).toEqual({ key: "security.issues.codeSixDigits" });
  });

  it("the proof field refuses only emptiness: a printed code is a whole answer", () => {
    expect(proofCodeIssue("123456")).toBeUndefined();
    expect(proofCodeIssue("aaaa-bbbb-cccc-dddd")).toBeUndefined();
    expect(proofCodeIssue("   ")).toEqual({ key: "security.issues.codeRequired" });
  });

  it("the password field refuses only emptiness, not the register floor", () => {
    expect(proofPasswordIssue("short")).toBeUndefined();
    expect(proofPasswordIssue("")).toEqual({ key: "security.issues.passwordRequired" });
  });
});
