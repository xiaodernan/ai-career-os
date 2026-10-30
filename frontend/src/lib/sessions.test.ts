import { describe, expect, it } from "vitest";

import { ApiError } from "@/lib/api/client";

import { deviceLabel, sessionCloseRefusal } from "./sessions";

/**
 * The sessions card's two non-markup decisions: what a stored user-agent is called on
 * screen, and which failed close the screen answers by refreshing rather than reporting.
 */
describe("deviceLabel", () => {
  it("names the browser and the system a real agent reports", () => {
    expect(
      deviceLabel(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Unnamed",
      ),
    ).toBe("Chrome · Windows");
    expect(
      deviceLabel(
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        "Unnamed",
      ),
    ).toBe("Safari · macOS");
  });

  it("does not call Edge or an iPhone's browser Chrome", () => {
    expect(
      deviceLabel(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
        "Unnamed",
      ),
    ).toBe("Edge · Windows");
    expect(
      deviceLabel(
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
        "Unnamed",
      ),
    ).toBe("Safari · iOS");
  });

  it("shows a name it cannot classify as itself, not as nothing", () => {
    expect(deviceLabel("JUnit/laptop", "Unnamed")).toBe("JUnit/laptop");
    expect(deviceLabel("  JUnit/phone  ", "Unnamed")).toBe("JUnit/phone");
  });

  it("answers the caller's fallback when the agent was never recorded", () => {
    expect(deviceLabel(null, "Unnamed device")).toBe("Unnamed device");
    expect(deviceLabel(undefined, "Unnamed device")).toBe("Unnamed device");
    expect(deviceLabel("   ", "Unnamed device")).toBe("Unnamed device");
  });
});

describe("sessionCloseRefusal", () => {
  it("reads the one 404 as a door that is already shut", () => {
    expect(sessionCloseRefusal(new ApiError("LOGIN_SESSION_NOT_FOUND", "Session not found", 404))).toBe(
      "gone",
    );
  });

  it("leaves every other refusal to the caller", () => {
    // A generic 404 is a route that does not exist, not a door that was closed; a 401
    // is the session ending, and a network failure never reached the server at all.
    expect(sessionCloseRefusal(new ApiError("NOT_FOUND", "No", 404))).toBeNull();
    expect(sessionCloseRefusal(new ApiError("UNAUTHORIZED", "No", 401))).toBeNull();
    expect(sessionCloseRefusal(new ApiError("RATE_LIMITED", "Slow down", 429))).toBeNull();
    expect(sessionCloseRefusal(new TypeError("Failed to fetch"))).toBeNull();
    expect(sessionCloseRefusal("not an error")).toBeNull();
  });
});
