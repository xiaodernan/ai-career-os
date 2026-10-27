import { defineConfig } from "vitest/config";
import { fileURLToPath } from "node:url";

export default defineConfig({
  test: {
    environment: "node",
    include: ["src/**/*.{test,spec}.{ts,tsx}"],
    css: false,
  },
  // Compile JSX the way Next does. esbuild defaults to the classic runtime, where every component
  // needs `React` in scope; Next's automatic runtime does not, so a component that renders in
  // production (e.g. ai-badge.tsx) crashed here with "React is not defined" -- a test-plane
  // artifact, not a product defect.
  esbuild: { jsx: "automatic" },
  // Pure-TS unit tests: don't load the app's Tailwind/PostCSS pipeline.
  css: { postcss: { plugins: [] } },
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
});
