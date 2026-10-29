import type { NextConfig } from "next";

/**
 * `output: "standalone"` is opt-in, because it and `next start` are mutually exclusive.
 *
 * Next warns "next start does not work with output: standalone" and then never binds the
 * port — so enabling it unconditionally silently breaks the local run *and* the E2E
 * suite, both of which serve the app with `next start`. It fails quietly: the process
 * prints "Ready" and listens on nothing. The Docker build opts in via NEXT_STANDALONE=1
 * to get the traced bundle; every other build stays one `next start` can serve.
 *
 * Why the image wants it: the Dockerfile used to copy the whole `node_modules` from the
 * build stage, which `npm ci` had filled with all 12 devDependencies — so the runtime
 * image shipped its own test runner, linter and CSS toolchain. Standalone contains only
 * what the server traces.
 */
/**
 * The browser is told what the shell may frame, sniff and use.
 *
 * A reverse proxy usually adds these, but the app is also served by `next start`
 * directly (local runs, the E2E suite), and a hardening rule that lives only in one
 * deployment's proxy is a rule every other run does not have. The app never embeds
 * itself in a frame; every byte it serves is declared by its own content type, so a
 * browser that guesses is guessing about data, not markup; and the one device feature
 * the product uses is the interview page's microphone, which stays available to this
 * origin while the camera and location the app never asks for are denied outright.
 *
 * The transport rule is the one header that bites a visitor rather than a page: a
 * browser that has seen the shell over https refuses a plain-http downgrade to the
 * same origin for a year. Browsers ignore STS delivered over http, so the local runs
 * and the E2E stack are untouched; `includeSubDomains` and `preload` are left out
 * because the shell may share a parent domain with services this repository does not
 * run, and the preload list is a commitment only the operator can make for their
 * hostname. A reverse proxy may add both around the app.
 *
 * The isolation pair closes the shell's handles: `Cross-Origin-Opener-Policy`
 * severs the link to a page on another origin that opened the app in a new window,
 * so that page cannot steer the shell's window or time its loads, and
 * `Cross-Origin-Resource-Policy` stops another origin reading the shell's answers as
 * subresources of its own. Both leave same-origin windows and fetches alone -- the
 * app's print window, its chunks, its manifest, the worker's own cache writes. The
 * config also stops answering `X-Powered-By: Next.js`, because the framework a
 * server runs is not a fact its visitors need.
 */
export const SECURITY_HEADERS = [
  { key: "X-Frame-Options", value: "DENY" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "camera=(), geolocation=(), microphone=(self)" },
  { key: "Cross-Origin-Opener-Policy", value: "same-origin" },
  { key: "Cross-Origin-Resource-Policy", value: "same-origin" },
  { key: "Strict-Transport-Security", value: "max-age=31536000" },
] as const;

const nextConfig: NextConfig = {
  ...(process.env.NEXT_STANDALONE === "1" ? { output: "standalone" as const } : {}),
  poweredByHeader: false,
  async headers() {
    return [{ source: "/:path*", headers: SECURITY_HEADERS.map((header) => ({ ...header })) }];
  },
};

export default nextConfig;
