import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /**
   * Emit a self-contained server bundle so the production image can ship only the
   * files and dependencies it actually traces.
   *
   * Without this, `frontend/Dockerfile` copies the whole `node_modules` from the
   * build stage — which `npm ci` populated with all 12 devDependencies (vitest,
   * playwright, eslint, typescript, tailwind). The runtime image then carried its
   * own test runner and linter: hundreds of megabytes, and a wider surface than the
   * app needs. Standalone keeps the regular `.next` too, so `next start` and the
   * local/E2E flow are unaffected.
   */
  output: "standalone",
};

export default nextConfig;
