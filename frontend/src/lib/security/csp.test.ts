import { describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api/endpoints", () => ({
  API_BASE_URL: "https://api.careeros.example/api/v1",
}));

import { apiOrigin, buildCsp } from "./csp";

const NONCE = "dGhpcy1pcy1hLW5vbmNl";

const shipped = {
  nonce: NONCE,
  apiOrigin: "http://localhost:8080",
  dev: false,
  secure: false,
} as const;

/** The policy as directive -> values, so a rule is asserted by name, not by order. */
function read(policy: string): Record<string, string[]> {
  const table: Record<string, string[]> = {};
  for (const part of policy.split(";")) {
    const [name, ...values] = part.trim().split(/\s+/);
    if (name) table[name] = values;
  }
  return table;
}

describe("the shell's content security policy", () => {
  it("trusts this answer's nonce and the scripts it loads, and nothing else", () => {
    const policy = read(buildCsp(shipped));
    expect(policy["script-src"]).toEqual(["'self'", `'nonce-${NONCE}'`, "'strict-dynamic'"]);
    expect(policy["script-src"]).not.toContain("'unsafe-inline'");
    expect(policy["script-src"]).not.toContain("'unsafe-eval'");
  });

  it("names this origin, the API's, and no third one", () => {
    const policy = read(buildCsp(shipped));
    expect(policy["default-src"]).toEqual(["'self'"]);
    expect(policy["connect-src"]).toEqual(["'self'", "http://localhost:8080"]);
    expect(policy["img-src"]).toEqual(["'self'", "data:", "blob:"]);
    expect(policy["media-src"]).toEqual(["'self'", "blob:"]);
    // The installable shell registers a worker from this origin.
    expect(policy["worker-src"]).toEqual(["'self'"]);
  });

  it("reads the API's origin, not its path", () => {
    expect(apiOrigin()).toBe("https://api.careeros.example");
  });

  it("lets only the development build evaluate its own modules", () => {
    const dev = read(buildCsp({ ...shipped, dev: true }));
    expect(dev["script-src"]).toContain("'unsafe-eval'");
    expect(dev["connect-src"]).toEqual(["'self'", "http://localhost:8080", "ws:", "wss:"]);
  });

  it("forbids what the product never uses", () => {
    const policy = read(buildCsp(shipped));
    expect(policy["object-src"]).toEqual(["'none'"]);
    expect(policy["base-uri"]).toEqual(["'self'"]);
    expect(policy["form-action"]).toEqual(["'self'"]);
    expect(policy["frame-ancestors"]).toEqual(["'none'"]);
    // Next writes the font variables and the first paint as inline style.
    expect(policy["style-src"]).toEqual(["'self'", "'unsafe-inline'"]);
    expect(policy["font-src"]).toEqual(["'self'", "data:"]);
  });

  it("asks for TLS only when the answer itself arrived over it", () => {
    expect(buildCsp(shipped)).not.toContain("upgrade-insecure-requests");
    expect(buildCsp({ ...shipped, secure: true })).toContain("upgrade-insecure-requests");
  });

  it("is one header line: a policy is not a place to smuggle a second header", () => {
    expect(buildCsp(shipped)).not.toMatch(/[\r\n]/);
  });
});
