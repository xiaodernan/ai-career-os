import { describe, expect, it } from "vitest";

import { ApiError } from "@/lib/api/client";

import { eraseRefusal } from "./erase-account";

/**
 * The erasure card's refusal mapping: which of the route's two named refusals belongs
 * under which field, and that every other answer stays with the shared describer.
 */
describe("eraseRefusal", () => {
  it("puts a wrong password under the password box", () => {
    expect(
      eraseRefusal(new ApiError("CURRENT_PASSWORD_INCORRECT", "Current password is incorrect", 401)),
    ).toBe("password");
  });

  it("puts an address that is not this account's under the address box", () => {
    expect(
      eraseRefusal(new ApiError("CONFIRMATION_MISMATCH", "The typed email does not match", 400)),
    ).toBe("email");
  });

  it("leaves every other refusal to the caller", () => {
    // A 404 is the account already gone, 429 is the limiter, 400 validation is a body the
    // form could not have sent; none of them is about one field.
    expect(eraseRefusal(new ApiError("USER_NOT_FOUND", "Gone", 404))).toBeNull();
    expect(eraseRefusal(new ApiError("RATE_LIMITED", "Slow down", 429))).toBeNull();
    expect(eraseRefusal(new ApiError("VALIDATION_FAILED", "Bad body", 400))).toBeNull();
    expect(eraseRefusal(new TypeError("Failed to fetch"))).toBeNull();
    expect(eraseRefusal("not an error")).toBeNull();
  });
});
