import { describe, expect, it } from "vitest";

import { ApiError } from "@/lib/api/client";
import {
  DISPLAY_NAME_MAX_LENGTH,
  EMAIL_MAX_LENGTH,
  PASSWORD_MAX_LENGTH,
  PASSWORD_MIN_LENGTH,
  RESET_TOKEN_MAX_LENGTH,
  confirmationIssue,
  displayNameIssue,
  emailIssue,
  passwordIssue,
  recoveryErrorMessage,
  resetTokenFrom,
  tokenIssue,
} from "./auth-recovery";

describe("emailIssue", () => {
  it("asks for an address when the field is empty", () => {
    expect(emailIssue("")).toBe("Email is required");
  });

  it("accepts the shapes the API's @Email accepts", () => {
    expect(emailIssue("ada@example.com")).toBeUndefined();
    expect(emailIssue("ada+career.os@sub.example.co.uk")).toBeUndefined();
  });

  it("catches the shapes it does not", () => {
    expect(emailIssue("ada@example")).toBe("Enter a valid email address");
    expect(emailIssue("ada example.com")).toBe("Enter a valid email address");
    expect(emailIssue("@example.com")).toBe("Enter a valid email address");
  });

  it("mirrors the size all three email records carry", () => {
    const longest = "a".repeat(EMAIL_MAX_LENGTH - "@example.com".length) + "@example.com";
    expect(longest).toHaveLength(EMAIL_MAX_LENGTH);
    expect(emailIssue(longest)).toBeUndefined();
    expect(emailIssue("a" + longest)).toBe("Use at most 255 characters");
  });
});

describe("passwordIssue", () => {
  it("asks for a password when the field is empty", () => {
    expect(passwordIssue("")).toBe("Password is required");
  });

  it("rejects the shortest value the backend would reject", () => {
    expect(passwordIssue("a".repeat(PASSWORD_MIN_LENGTH - 1))).toBe("Use at least 8 characters");
  });

  it("accepts the boundaries the backend accepts", () => {
    expect(passwordIssue("a".repeat(PASSWORD_MIN_LENGTH))).toBeUndefined();
    expect(passwordIssue("a".repeat(PASSWORD_MAX_LENGTH))).toBeUndefined();
  });

  it("rejects what BCrypt would have to truncate", () => {
    expect(passwordIssue("a".repeat(PASSWORD_MAX_LENGTH + 1))).toBe("Use at most 72 characters");
  });

  it("counts characters, not bytes, so a CJK passphrase is judged as typed", () => {
    expect(passwordIssue("口令口令口令口令")).toBeUndefined();
  });
});

describe("displayNameIssue", () => {
  it("asks for a name when the field is empty or only whitespace", () => {
    expect(displayNameIssue("")).toBe("Name is required");
    expect(displayNameIssue("   ")).toBe("Name is required");
  });

  it("accepts the register record's ceiling and refuses one character more", () => {
    expect(displayNameIssue("A".repeat(DISPLAY_NAME_MAX_LENGTH))).toBeUndefined();
    expect(displayNameIssue("A".repeat(DISPLAY_NAME_MAX_LENGTH + 1))).toBe(
      "Use at most 120 characters",
    );
  });
});

describe("confirmationIssue", () => {
  it("asks for the confirmation when the field is empty", () => {
    expect(confirmationIssue("", "correct horse")).toBe("Confirm your new password");
  });

  it("reports a mismatch", () => {
    expect(confirmationIssue("correct hors", "correct horse")).toBe("Passwords do not match");
  });

  it("is quiet once the two agree", () => {
    expect(confirmationIssue("correct horse", "correct horse")).toBeUndefined();
  });
});

describe("tokenIssue", () => {
  it("asks for the token when the field is empty or only whitespace", () => {
    expect(tokenIssue("")).toBe("Paste the token from your email");
    expect(tokenIssue("   ")).toBe("Paste the token from your email");
  });

  it("does not second-guess the shape, since only the API can judge a token", () => {
    // A short token is refused by the API with RESET_TOKEN_INVALID, which the screen turns into
    // advice; rejecting it here would replace that advice with a guess about the alphabet.
    expect(tokenIssue("abc")).toBeUndefined();
    expect(tokenIssue("Xk3-9_aB.~$")).toBeUndefined();
  });

  it("refuses a paste longer than the reset record accepts", () => {
    expect(tokenIssue("x".repeat(RESET_TOKEN_MAX_LENGTH))).toBeUndefined();
    expect(tokenIssue("x".repeat(RESET_TOKEN_MAX_LENGTH + 1))).toBe(
      "Use at most 512 characters",
    );
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
      "That reset link is invalid or has expired. Request a new one.",
    );
  });

  it("passes any other API message through, since validation messages are actionable", () => {
    const err = new ApiError("VALIDATION_FAILED", "newPassword: size must be between 8 and 72", 400);
    expect(recoveryErrorMessage(err)).toBe("newPassword: size must be between 8 and 72");
  });

  it("names the network as the cause when fetch never reached a server", () => {
    expect(recoveryErrorMessage(new TypeError("Failed to fetch"))).toBe(
      "Cannot reach the API — is the backend running?",
    );
  });

  it("has something to say for anything else", () => {
    expect(recoveryErrorMessage(new Error("boom"))).toBe("Something went wrong. Please try again.");
  });
});
