import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

/**
 * Epic 432 — the data door holds export/redact/restore: the highest-consequence
 * actions in the product. Every one must teach what it does before a reader
 * presses it, and the import field must use the boxless span anchor so the
 * tooltip never writes data-state over the textarea.
 */
describe("Data-page teaching hints", () => {
  const source = readFileSync(resolve(__dirname, "./page.tsx"), "utf8");

  it("teaches all nine export, redact and restore controls", () => {
    for (const key of [
      "data.hintExportEverything",
      "data.hintExportAnonymized",
      "data.hintDownloadJson",
      "data.hintPrintView",
      "data.hintDownloadMarkdown",
      "data.hintRedactSelected",
      "data.hintImportBundle",
      "data.hintBuildPlan",
      "data.hintApplyRestore",
    ]) {
      expect(source, key).toContain(`"${key}"`);
    }
  });

  it("uses the boxless span anchor on the import textarea", () => {
    expect(source).toContain('anchor="span" label={t("data.hintImportBundle")}');
  });

  it("still has the preview-then-apply pair — a restore must be readable before it writes", () => {
    expect(source).toContain("data.hintBuildPlan");
    expect(source).toContain("data.hintApplyRestore");
    expect(source.indexOf("data.hintBuildPlan")).toBeLessThan(source.indexOf("data.hintApplyRestore"));
  });
});
