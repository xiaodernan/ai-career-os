import { describe, expect, it } from "vitest";
import nextConfig, { SECURITY_HEADERS } from "../../next.config";

describe("the shell's browser headers", () => {
  it("every path carries all four, with the microphone kept for this origin", async () => {
    expect(nextConfig.headers).toBeTypeOf("function");
    const rules = await nextConfig.headers!();
    expect(rules).toHaveLength(1);
    expect(rules[0].source).toBe("/:path*");
    expect(rules[0].headers).toEqual([
      { key: "X-Frame-Options", value: "DENY" },
      { key: "X-Content-Type-Options", value: "nosniff" },
      { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
      { key: "Permissions-Policy", value: "camera=(), geolocation=(), microphone=(self)" },
    ]);
    // The rule is derived from the one exported list, so a header added to the list
    // cannot skip the rule and a rule that stops carrying the list is a red here.
    expect(rules[0].headers).toHaveLength(SECURITY_HEADERS.length);
  });
});
