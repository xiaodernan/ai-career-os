import { describe, expect, it } from "vitest";
import { newRequestId } from "./client";

// The backend RequestIdFilter and the ai-service middleware agree on this alphabet:
// 8-64 chars of letters, digits, dot, dash or underscore. A browser-minted id that
// breaks that shape is silently replaced server-side, which defeats the point of
// frontend→backend trace correlation.
const ACCEPTED = /^[A-Za-z0-9][A-Za-z0-9._-]{7,63}$/;

describe("newRequestId", () => {
  it("matches the server-accepted alphabet", () => {
    for (let i = 0; i < 50; i += 1) {
      expect(newRequestId()).toMatch(ACCEPTED);
    }
  });

  it("mints distinct ids", () => {
    const ids = new Set(Array.from({ length: 32 }, () => newRequestId()));
    expect(ids.size).toBe(32);
  });
});
