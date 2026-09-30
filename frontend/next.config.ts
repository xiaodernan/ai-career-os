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
const nextConfig: NextConfig = {
  ...(process.env.NEXT_STANDALONE === "1" ? { output: "standalone" as const } : {}),
};

export default nextConfig;
