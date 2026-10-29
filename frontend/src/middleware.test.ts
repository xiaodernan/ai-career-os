import { NextRequest } from "next/server";
import { describe, expect, it } from "vitest";

import { config, middleware } from "./middleware";

function answer(url: string): { policy: string; nonce: string } {
  const policy = middleware(new NextRequest(url)).headers.get("content-security-policy") ?? "";
  return { policy, nonce: /'nonce-([^']+)'/.exec(policy)?.[1] ?? "" };
}

describe("the shell's policy travels with every answer", () => {
  it("mints a new nonce on every answer", () => {
    const first = answer("http://localhost:3000/dashboard");
    const second = answer("http://localhost:3000/dashboard");
    expect(first.nonce).not.toBe("");
    expect(second.nonce).not.toBe(first.nonce);
  });

  it("does not put the policy on the build's hashed bytes", () => {
    expect(config.matcher).toBe("/((?!_next/static|_next/image|favicon.ico).*)");
  });

  it("asks for TLS only when the request itself arrived over it", () => {
    expect(answer("http://localhost:3000/").policy).not.toContain("upgrade-insecure-requests");
    expect(answer("https://careeros.example/").policy).toContain("upgrade-insecure-requests");
  });
});
