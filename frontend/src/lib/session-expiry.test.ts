import { describe, expect, it } from "vitest";

import { SESSION_EXPIRED_MESSAGE, SESSION_EXPIRED_REASON, sessionNotice } from "./session-expiry";

describe("sessionNotice", () => {
  it("resolves the announcement for the reason the bounce writes", () => {
    expect(sessionNotice(SESSION_EXPIRED_REASON)).toBe(SESSION_EXPIRED_MESSAGE);
  });

  it("stays silent on absent, malformed or unrelated reasons", () => {
    for (const reason of [undefined, null, "", " ", "Expired", "expired ", "signed-out"]) {
      expect(sessionNotice(reason)).toBeUndefined();
    }
  });

  it("says why the user is here and what to do next", () => {
    const sentence = SESSION_EXPIRED_MESSAGE.toLowerCase();
    expect(sentence).toContain("session has expired");
    expect(sentence).toContain("sign in");
  });
});
