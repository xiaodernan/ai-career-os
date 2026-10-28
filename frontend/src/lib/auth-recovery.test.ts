import { describe, expect, it } from "vitest";

import { ApiError } from "@/lib/api/client";
import {
  DISPLAY_NAME_MAX_LENGTH,
  EMAIL_MAX_LENGTH,
  PASSWORD_MAX_LENGTH,
  PASSWORD_MIN_LENGTH,
  RESET_TOKEN_MAX_LENGTH,
  authFormErrorMessage,
  confirmationIssue,
  displayNameIssue,
  emailIssue,
  networkFailure,
  passwordIssue,
  recoveryErrorMessage,
  resetTokenFrom,
  tokenIssue,
} from "./auth-recovery";
import { issueText, type TextIssue } from "./i18n/issue";
import { fill, lookup } from "./i18n/locale-context";
import { translations } from "./i18n/translations";

/**
 * A translator that reads a real table, the way the provider's `t` does.
 *
 * The tests below hold the checks to *keys*, because that is what the screens
 * consume; the sentences are pinned only where the wiring is the point --
 * which key answers, and whether the holes in it get their values.
 */
function reader(table: unknown) {
  return (key: string, vars?: Record<string, string | number>) => {
    const value = lookup(table, key);
    if (value === undefined) throw new Error(`the table has no ${key}`);
    return fill(value, vars);
  };
}

const en = reader(translations.en);
const zh = reader(translations.zh);

/** A check's answer is the sentence's identity, not a sentence. */
function expectIssue(issue: TextIssue | undefined, key: string, params?: Record<string, string | number>) {
  expect(issue).toEqual(params === undefined ? { key } : { key, params });
}

describe("emailIssue", () => {
  it("asks for an address when the field is empty", () => {
    expectIssue(emailIssue(""), "auth.issues.emailRequired");
  });

  it("accepts the shapes the API's @Email accepts", () => {
    expect(emailIssue("ada@example.com")).toBeUndefined();
    expect(emailIssue("ada+career.os@sub.example.co.uk")).toBeUndefined();
  });

  it("catches the shapes it does not", () => {
    expectIssue(emailIssue("ada@example"), "auth.issues.emailInvalid");
    expectIssue(emailIssue("ada example.com"), "auth.issues.emailInvalid");
    expectIssue(emailIssue("@example.com"), "auth.issues.emailInvalid");
  });

  it("mirrors the size all three email records carry", () => {
    const longest = "a".repeat(EMAIL_MAX_LENGTH - "@example.com".length) + "@example.com";
    expect(longest).toHaveLength(EMAIL_MAX_LENGTH);
    expect(emailIssue(longest)).toBeUndefined();
    expectIssue(emailIssue("a" + longest), "auth.issues.tooLong", { max: EMAIL_MAX_LENGTH });
  });
});

describe("passwordIssue", () => {
  it("asks for a password when the field is empty", () => {
    expectIssue(passwordIssue(""), "auth.issues.passwordRequired");
  });

  it("rejects the shortest value the backend would reject", () => {
    expectIssue(passwordIssue("a".repeat(PASSWORD_MIN_LENGTH - 1)), "auth.issues.tooShort", {
      min: PASSWORD_MIN_LENGTH,
    });
  });

  it("accepts the boundaries the backend accepts", () => {
    expect(passwordIssue("a".repeat(PASSWORD_MIN_LENGTH))).toBeUndefined();
    expect(passwordIssue("a".repeat(PASSWORD_MAX_LENGTH))).toBeUndefined();
  });

  it("rejects what BCrypt would have to truncate", () => {
    expectIssue(passwordIssue("a".repeat(PASSWORD_MAX_LENGTH + 1)), "auth.issues.tooLong", {
      max: PASSWORD_MAX_LENGTH,
    });
  });

  it("counts characters, not bytes, so a CJK passphrase is judged as typed", () => {
    expect(passwordIssue("口令口令口令口令")).toBeUndefined();
  });
});

describe("displayNameIssue", () => {
  it("asks for a name when the field is empty or only whitespace", () => {
    expectIssue(displayNameIssue(""), "auth.issues.nameRequired");
    expectIssue(displayNameIssue("   "), "auth.issues.nameRequired");
  });

  it("accepts the register record's ceiling and refuses one character more", () => {
    expect(displayNameIssue("A".repeat(DISPLAY_NAME_MAX_LENGTH))).toBeUndefined();
    expectIssue(displayNameIssue("A".repeat(DISPLAY_NAME_MAX_LENGTH + 1)), "auth.issues.tooLong", {
      max: DISPLAY_NAME_MAX_LENGTH,
    });
  });
});

describe("confirmationIssue", () => {
  it("asks for the confirmation when the field is empty", () => {
    expectIssue(confirmationIssue("", "correct horse"), "auth.issues.confirmRequired");
  });

  it("reports a mismatch", () => {
    expectIssue(confirmationIssue("correct hors", "correct horse"), "auth.passwordsDoNotMatch");
  });

  it("is quiet once the two agree", () => {
    expect(confirmationIssue("correct horse", "correct horse")).toBeUndefined();
  });
});

describe("tokenIssue", () => {
  it("asks for the token when the field is empty or only whitespace", () => {
    expectIssue(tokenIssue(""), "auth.issues.tokenRequired");
    expectIssue(tokenIssue("   "), "auth.issues.tokenRequired");
  });

  it("does not second-guess the shape, since only the API can judge a token", () => {
    // A short token is refused by the API with RESET_TOKEN_INVALID, which the screen turns into
    // advice; rejecting it here would replace that advice with a guess about the alphabet.
    expect(tokenIssue("abc")).toBeUndefined();
    expect(tokenIssue("Xk3-9_aB.~$")).toBeUndefined();
  });

  it("refuses a paste longer than the reset record accepts", () => {
    expect(tokenIssue("x".repeat(RESET_TOKEN_MAX_LENGTH))).toBeUndefined();
    expectIssue(
      tokenIssue("x".repeat(RESET_TOKEN_MAX_LENGTH + 1)),
      "auth.issues.tooLong",
      { max: RESET_TOKEN_MAX_LENGTH },
    );
  });
});

describe("issueText", () => {
  it("has nothing to say about no issue", () => {
    expect(issueText(undefined, en)).toBeUndefined();
  });

  it("fills the holes with the bound the check used", () => {
    expect(issueText(emailIssue("a".repeat(EMAIL_MAX_LENGTH + 1)), en)).toBe(
      `Use at most ${EMAIL_MAX_LENGTH} characters`,
    );
    expect(issueText(passwordIssue("a"), zh)).toContain(String(PASSWORD_MIN_LENGTH));
  });

  it("has a sentence in both languages for every issue a check can answer", () => {
    // These keys live in object literals, so the literal-key gate cannot
    // see them: it scans for `t("...")`, and the checks answer with
    // `{ key: "..." }`. This is the gate for that shape.
    const issues = [
      emailIssue(""),
      emailIssue("nope"),
      emailIssue("a".repeat(EMAIL_MAX_LENGTH + 1)),
      passwordIssue(""),
      passwordIssue("a"),
      passwordIssue("a".repeat(PASSWORD_MAX_LENGTH + 1)),
      displayNameIssue(""),
      displayNameIssue("A".repeat(DISPLAY_NAME_MAX_LENGTH + 1)),
      tokenIssue(""),
      tokenIssue("x".repeat(RESET_TOKEN_MAX_LENGTH + 1)),
      confirmationIssue("", "correct horse"),
      confirmationIssue("correct hors", "correct horse"),
    ];
    for (const issue of issues) {
      expect(issue).toBeDefined();
      if (issue === undefined) continue;
      for (const [language, t] of [
        ["en", en],
        ["zh", zh],
      ] as const) {
        const sentence = issueText(issue, t);
        expect(sentence, `${issue.key} has no ${language} sentence`).toBeTruthy();
        // A hole the sentence names and the check does not fill would reach
        // the reader as "{max}"; the values are the check's own params, so
        // any brace left over is a mismatch between the two spellings.
        expect(sentence, `${issue.key}'s ${language} sentence has an unfilled hole`).not.toMatch(
          /\{\w+\}/,
        );
      }
    }
  });
});

describe("resetTokenFrom", () => {
  it("reads the token out of the link the mail carries", () => {
    expect(resetTokenFrom("?token=Xk3-9_aB")).toBe("Xk3-9_aB");
  });

  it("finds it beside the other params a link might carry", () => {
    expect(resetTokenFrom("?next=%2Fsettings&token=Xk3")).toBe("Xk3");
  });

  it("trims what a pasted URL picked up", () => {
    expect(resetTokenFrom("?token=%20Xk3%20")).toBe("Xk3");
  });

  it("has no token when the link is bare, blank or empty", () => {
    expect(resetTokenFrom("")).toBeNull();
    expect(resetTokenFrom("?next=/dashboard")).toBeNull();
    expect(resetTokenFrom("?token=")).toBeNull();
    expect(resetTokenFrom("?token=%20%20")).toBeNull();
  });
});

describe("recoveryErrorMessage", () => {
  it("turns the API's token complaint into what to do next", () => {
    const err = new ApiError("RESET_TOKEN_INVALID", "Invalid reset token", 400);
    expect(recoveryErrorMessage(err)).toBe(
      "That reset link is invalid or has expired. Please request a new one.",
    );
  });

  it("passes any other API message through, since validation messages are actionable", () => {
    const err = new ApiError("VALIDATION_FAILED", "newPassword: size must be between 8 and 72", 400);
    expect(recoveryErrorMessage(err)).toBe("newPassword: size must be between 8 and 72");
  });

  it("names the network as the cause when fetch never reached a server", () => {
    expect(recoveryErrorMessage(new TypeError("Failed to fetch"))).toBe(networkFailure());
    expect(networkFailure()).toBe("Cannot reach the API — is the backend running?");
  });

  it("has something to say for anything else", () => {
    expect(recoveryErrorMessage(new Error("boom"))).toBe("Something went wrong. Please try again.");
  });

  it("speaks the language the reader chose", () => {
    const scope = globalThis as { window?: unknown };
    const previous = scope.window;
    scope.window = { localStorage: { getItem: () => "zh" } };
    try {
      expect(
        recoveryErrorMessage(new ApiError("RESET_TOKEN_INVALID", "Invalid reset token", 400)),
      ).toBe(zh("errorCodes.RESET_TOKEN_INVALID"));
      expect(recoveryErrorMessage(new TypeError("Failed to fetch"))).toBe(
        zh("errorCodes.NETWORK_ERROR"),
      );
    } finally {
      if (previous === undefined) delete scope.window;
      else scope.window = previous;
    }
  });
});

describe("authFormErrorMessage", () => {
  it("answers a 401 with the sentence that names neither field", () => {
    // The API says "Invalid credentials"; telling the user which of the two fields
    // was wrong would tell an attacker which one was right.
    const api401 = new ApiError("INVALID_CREDENTIALS", "Invalid credentials", 401);
    expect(authFormErrorMessage(api401)).toBe("That email address or password is not right.");
    // ...and the status alone still triggers it, because the code spelling used to
    // be AUTH_INVALID_CREDENTIALS — a name the backend never sends (the vocabulary
    // has INVALID_CREDENTIALS), which is why the friendly sentence only ever
    // fired through the status half and nobody noticed the dead check.
    const bare401 = new ApiError("SOMETHING_ELSE", "no", 401);
    expect(authFormErrorMessage(bare401)).toBe("That email address or password is not right.");
  });

  it("passes other API messages through, since validation messages are actionable", () => {
    const err = new ApiError("VALIDATION_FAILED", "email: must be a well-formed address", 400);
    expect(authFormErrorMessage(err)).toBe("email: must be a well-formed address");
    expect(authFormErrorMessage(new ApiError("EMAIL_ALREADY_REGISTERED", "taken", 409))).toBe("taken");
  });

  it("composes the recovery describer for the network and the unknown", () => {
    expect(authFormErrorMessage(new TypeError("Failed to fetch"))).toBe(networkFailure());
    expect(authFormErrorMessage(new Error("boom"))).toBe("Something went wrong. Please try again.");
  });
});
