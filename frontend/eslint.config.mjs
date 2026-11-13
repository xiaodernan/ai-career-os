import { dirname } from "path";
import { fileURLToPath } from "url";
import { FlatCompat } from "@eslint/eslintrc";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const compat = new FlatCompat({
  baseDirectory: __dirname,
});

const eslintConfig = [
  ...compat.extends("next/core-web-vitals", "next/typescript"),
  {
    ignores: [
      "node_modules/**",
      ".next/**",
      // Stale build snapshots some session left behind ("pre-interviews",
      // ".next.<marker>"): minified server bundles lint as require() errors, and
      // the directory is a gitignored artifact, not source. A glob so any future
      // snapshot lands here too instead of in a lint report.
      ".next.*/**",
      "out/**",
      "build/**",
      "next-env.d.ts",
    ],
  },
];

export default eslintConfig;
