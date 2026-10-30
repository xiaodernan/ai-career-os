import { describe, expect, it } from "vitest";

import { ApiError } from "@/lib/api/client";

import { currentPasswordIssue, passwordChangeRefusal } from "./password-change";

/**
 * The password card's two non-markup decisions: the current field's bounds, copied from
 * `PasswordChangeRequest`, and which refused change belongs under which input.
 */
describe("currentPasswordIssue", () => {
  it("asks for the current password before anything else", () => {
    expect(currentPasswordIssue("")).toEqual({ key: "auth.issues.passwordRequired" });
  });

  it("mirrors the record's ceiling on the current value", () => {
    // `@NotBlank @Size(max = 72)` -- the record sets no minimum on the current password,
    // so an account seeded before the 8-character rule still re-authenticates here.
    expect(currentPasswordIssue("short")).toBeUndefined();
    expect(currentPasswordIssue("x".repeat(72))).toBeUndefined();
    expect(currentPasswordIssue("x".repeat(73))).toEqual({
      key: "auth.issues.tooLong",
      params: { max: 72 },
    });
  });
});

describe("passwordChangeRefusal", () => {
  it("puts a rejected re-authentication under the current field", () => {
    expect(
      passwordChangeRefusal(new ApiError("CURRENT_PASSWORD_INCORRECT", "Wrong password", 401)),
    ).toBe("current");
  });

  it("puts a new value equal to the old one under the new field", () => {
    // Refused by name: the server declines before writing, so nothing was revoked and the
    // reader is being told to pick a different value, not that something went wrong.
    expect(passwordChangeRefusal(new ApiError("PASSWORD_UNCHANGED", "Same password", 400))).toBe(
      "new",
    );
  });

  it("leaves the limiter and everything unattributable to the form", () => {
    expect(passwordChangeRefusal(new ApiError("RATE_LIMITED", "Slow down", 429))).toBeNull();
    expect(passwordChangeRefusal(new ApiError("VALIDATION_FAILED", "No", 400))).toBeNull();
    expect(passwordChangeRefusal(new TypeError("Failed to fetch"))).toBeNull();
    expect(passwordChangeRefusal("not an error")).toBeNull();
  });
});
