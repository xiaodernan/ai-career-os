import { describe, expect, it } from "vitest";

import { ApiError } from "@/lib/api/client";

import { emailChangeOutcome, emailChangeTokenFrom, addressMoveRefusal } from "./email-change";

/**
 * The landing page's two decisions, held apart from the screen.
 *
 * The reset flow's arithmetic lives in `auth-recovery.ts` for the same reason: what is
 * worth pinning is not the markup, it is where the token comes from and which refusal
 * earns which sentence. The API collapses unknown, spent, expired and ownerless links
 * into one answer on purpose, so a page that tried to tell them apart would be
 * inventing a distinction the route refuses to make.
 */
describe("emailChangeTokenFrom", () => {
  it("reads the token the letter's link carries", () => {
    expect(emailChangeTokenFrom("?token=abc123")).toBe("abc123");
    expect(emailChangeTokenFrom("?from=mail&token=abc123&lang=en")).toBe("abc123");
  });

  it("trims what a paste leaves around the token", () => {
    expect(emailChangeTokenFrom("?token=%20abc123%20")).toBe("abc123");
  });

  it("answers null for a link that cannot answer itself", () => {
    expect(emailChangeTokenFrom("")).toBeNull();
    expect(emailChangeTokenFrom("?token=")).toBeNull();
    expect(emailChangeTokenFrom("?token=%20%20")).toBeNull();
    expect(emailChangeTokenFrom("?next=/dashboard")).toBeNull();
  });
});

describe("emailChangeOutcome", () => {
  it("reads the one answer for an unusable link", () => {
    expect(emailChangeOutcome(new ApiError("EMAIL_CHANGE_INVALID", "Invalid token", 400))).toBe(
      "invalid",
    );
  });

  it("keeps the race with a registration as its own answer", () => {
    // The token was spent before the address was checked (26.2), so the same link can
    // never succeed on a retry -- the screen must not offer one.
    expect(
      emailChangeOutcome(new ApiError("EMAIL_ALREADY_REGISTERED", "Registered", 409)),
    ).toBe("registered");
  });

  it("leaves every other refusal to the toast", () => {
    // A rate-limited call and a stale-tab 401 are transient or session-shaped; neither
    // is terminal for the link, so neither replaces the page's state.
    expect(emailChangeOutcome(new ApiError("RATE_LIMITED", "Slow down", 429))).toBeNull();
    expect(emailChangeOutcome(new ApiError("CURRENT_PASSWORD_INCORRECT", "No", 401))).toBeNull();
    expect(emailChangeOutcome(new ApiError("NETWORK_ERROR", "Down", 503))).toBeNull();
  });

  it("does not claim a failed fetch was the server's refusal", () => {
    expect(emailChangeOutcome(new TypeError("Failed to fetch"))).toBeNull();
    expect(emailChangeOutcome("not an error")).toBeNull();
  });
});

/**
 * The settings card's half of the same wire (38.2).
 *
 * The API names the reason on the code and never says which field was at fault, so the
 * card has to put each refusal under the field that caused it -- a password complaint
 * above the address box would send the reader to edit the wrong thing. Anything the
 * classifier does not recognise is the shared describer's sentence on the form, never a
 * guessed field.
 */
describe("addressMoveRefusal", () => {
  it("puts a wrong password under the password box", () => {
    expect(
      addressMoveRefusal(new ApiError("CURRENT_PASSWORD_INCORRECT", "Wrong password", 401)),
    ).toBe("password");
  });

  it("puts both address refusals under the address box", () => {
    expect(addressMoveRefusal(new ApiError("EMAIL_UNCHANGED", "Same address", 400))).toBe("email");
    expect(
      addressMoveRefusal(new ApiError("EMAIL_ALREADY_REGISTERED", "Taken", 409)),
    ).toBe("email");
  });

  it("keeps the limiter's answer at the form, because no field caused it", () => {
    expect(addressMoveRefusal(new ApiError("RATE_LIMITED", "Slow down", 429))).toBe("form");
  });

  it("attributes nothing it does not recognise", () => {
    expect(addressMoveRefusal(new ApiError("BAD_REQUEST", "Bad", 400))).toBeNull();
    expect(addressMoveRefusal(new TypeError("Failed to fetch"))).toBeNull();
    expect(addressMoveRefusal("not an error")).toBeNull();
  });
});
