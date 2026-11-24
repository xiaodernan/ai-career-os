import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/lib/i18n/locale-context", () => ({
  useLocale: () => ({
    locale: "en",
    t: (key: string) => `[${key}]`,
    setLocale: () => undefined,
  }),
}));

/**
 * Epic 431 — Match Studio is the page a candidate opens the moment a posting lands;
 * its five controls must teach what they do. Inputs use the boxless span anchor so
 * the tooltip never writes data-state over the field's own state.
 */
describe("Studio teaching hints", () => {
  const source = readFileSync(resolve(__dirname, "./page.tsx"), "utf8");

  it("teaches the posting box, resume version, analyze, tailor and copy", () => {
    for (const key of [
      "studio.hintJdInput",
      "studio.hintResumeVersion",
      "studio.hintAnalyze",
      "studio.hintTailor",
      "studio.hintCopy",
    ]) {
      expect(source, key).toContain(`"${key}"`);
    }
  });

  it("uses the boxless span anchor on the two stateful fields", () => {
    // Textarea and Input own their state; wrapping them directly would let the
    // tooltip's data-state replace it. The span anchor keeps the two independent.
    expect(source).toContain('anchor="span" label={t("studio.hintJdInput")}');
    expect(source).toContain('anchor="span" label={t("studio.hintResumeVersion")}');
  });
});
