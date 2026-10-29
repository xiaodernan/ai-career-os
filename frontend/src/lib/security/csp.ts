import { API_BASE_URL } from "@/lib/api/endpoints";

/**
 * The shell's content security policy.
 *
 * The seven headers in `next.config.ts` are the same on every answer, but a script
 * nonce cannot be: it is minted per response, so the policy is built in the
 * middleware and this module is the one place its rules live. It is pure, so the
 * gate can read every rule without a server.
 *
 * `strict-dynamic` lets the nonce trust Next's bootstrap script, and that script
 * trusts the chunks it imports; a host allowlist would be the older, weaker road.
 * The development build evaluates its own hot modules, so only development gets
 * `'unsafe-eval'`.
 */
export interface CspOptions {
  readonly nonce: string;
  readonly apiOrigin: string;
  readonly dev: boolean;
  readonly secure: boolean;
}

export function buildCsp({ nonce, apiOrigin, dev, secure }: CspOptions): string {
  const script = ["'self'", `'nonce-${nonce}'`, "'strict-dynamic'"];
  if (dev) script.push("'unsafe-eval'");
  const connect = ["'self'", apiOrigin];
  if (dev) connect.push("ws:", "wss:");
  const directives = [
    "default-src 'self'",
    `script-src ${script.join(" ")}`,
    // Next writes the fonts' variables and the first paint as inline style.
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: blob:",
    "font-src 'self' data:",
    `connect-src ${connect.join(" ")}`,
    // The interview page records and replays the reader's own voice.
    "media-src 'self' blob:",
    // The installable shell's worker is served from this origin.
    "worker-src 'self'",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    // The refusal `X-Frame-Options: DENY` makes, for browsers that read only one.
    "frame-ancestors 'none'",
  ];
  // A plain-http local run has no TLS to upgrade to, and asking would rewrite the
  // API's own http address into an https one the server does not answer.
  if (secure) directives.push("upgrade-insecure-requests");
  return directives.join("; ");
}

/** The API's origin, without its path: the only other host the browser may reach. */
export function apiOrigin(): string {
  return new URL(API_BASE_URL).origin;
}
