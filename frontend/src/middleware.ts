import { NextResponse, type NextRequest } from "next/server";

import { apiOrigin, buildCsp } from "@/lib/security/csp";

/**
 * Every answer leaves with a nonce, and a policy that names it.
 *
 * Next reads the `Content-Security-Policy` request header and stamps the scripts it
 * emits with the nonce it finds; the response header is the one the browser
 * enforces. The nonce is new on every answer, so a script injected into one answer
 * cannot run in the next.
 */
export function middleware(request: NextRequest) {
  const nonce = btoa(crypto.randomUUID());
  const policy = buildCsp({
    nonce,
    apiOrigin: apiOrigin(),
    dev: process.env.NODE_ENV !== "production",
    secure: request.nextUrl.protocol === "https:",
  });
  const requestHeaders = new Headers(request.headers);
  requestHeaders.set("x-nonce", nonce);
  requestHeaders.set("Content-Security-Policy", policy);
  const response = NextResponse.next({ request: { headers: requestHeaders } });
  response.headers.set("Content-Security-Policy", policy);
  return response;
}

// The build's hashed chunks are bytes, not documents: they run under the page's
// policy, and a nonce on a file shared by every reader would be a nonce reused.
export const config = {
  matcher: "/((?!_next/static|_next/image|favicon.ico).*)",
};
