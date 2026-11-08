import { defineConfig } from "vitest/config";
import { fileURLToPath } from "node:url";

export default defineConfig({
  test: {
    environment: "node",
    include: ["src/**/*.{test,spec}.{ts,tsx}"],
    css: false,
    // Several tests sweep the repo from disk (route parity, census). 5s is not
    // enough on a loaded machine; keep the cap generous without masking a hang.
    testTimeout: 15000,
  },
  // Compile JSX the way Next does: vite 8 transforms with oxc, which must be told
  // to use the automatic runtime explicitly (esbuild options are ignored in favor
  // of oxc). Pure-TS unit tests: don't load the app's Tailwind/PostCSS pipeline.
  oxc: { jsx: "automatic" },
  css: { postcss: { plugins: [] } },
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
});
