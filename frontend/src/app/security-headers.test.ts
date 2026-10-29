import { describe, expect, it } from "vitest";
import nextConfig, { SECURITY_HEADERS } from "../../next.config";

describe("the shell's browser headers", () => {
  it("every path carries all five, with the microphone kept for this origin", async () => {
    expect(nextConfig.headers).toBeTypeOf("function");
    const rules = await nextConfig.headers!();
    expect(rules).toHaveLength(1);
    expect(rules[0].source).toBe("/:path*");
    expect(rules[0].headers).toEqual([
      { key: "X-Frame-Options", value: "DENY" },
      { key: "X-Content-Type-Options", value: "nosniff" },
      { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
      { key: "Permissions-Policy", value: "camera=(), geolocation=(), microphone=(self)" },
      { key: "Strict-Transport-Security", value: "max-age=31536000" },
    ]);
    // The rule is derived from the one exported list, so a header added to the list
    // cannot skip the rule and a rule that stops carrying the list is a red here.
    expect(rules[0].headers).toHaveLength(SECURITY_HEADERS.length);
  });

  it("the transport rule pins a year and nothing else", () => {
    const value = SECURITY_HEADERS.find(
      (header) => header.key === "Strict-Transport-Security",
    )?.value ?? "";
    // The value is the whole directive list, so a future `includeSubDomains` or
    // `preload` cannot arrive by accident: both extend the promise to hosts the
    // operator has not agreed to pin, and the years floor is the one browsers honour.
    const maxAge = /^max-age=(\d+)$/.exec(value);
    expect(maxAge).not.toBeNull();
    expect(Number(maxAge ? maxAge[1] : NaN)).toBeGreaterThanOrEqual(31536000);
  });
});
