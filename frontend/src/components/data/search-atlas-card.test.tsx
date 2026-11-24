import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it, vi } from "vitest";
import { lookup } from "@/lib/i18n/locale-context";
import { translations } from "@/lib/i18n/translations";

/**
 * Epic 438 — the atlas card is the browser's door to the pure map engine. It must
 * derive its payload from the export bundle already in hand (no new read), pin
 * every region key the engine emits, and carry bilingual copy with a teaching
 * hint on the one control.
 */
const CARD = readFileSync(resolve(__dirname, "./search-atlas-card.tsx"), "utf8");
const HOOK = readFileSync(resolve(__dirname, "../../lib/hooks/timeline.ts"), "utf8");

describe("Search atlas card (Epic 438)", () => {
  it("derives all seven regions from the export bundle, not from new reads", () => {
    for (const [payload, section] of [
      ["applications", "applications"],
      ["jobs", "saved_jobs"],
      ["interviews", "interviews"],
      ["letters", "cover_letters"],
      ["notes", "notes"],
      ["contacts", "contacts"],
      ["offers", "offers"],
    ]) {
      expect(CARD, payload).toContain(`${payload}: rows(data.${section})`);
    }
    expect(CARD).not.toMatch(/useQuery|api\.get|fetch\(/);
  });

  it("sends every key through the typed hook with the locale attached", () => {
    for (const key of [
      "applications", "jobs", "interviews", "letters", "notes", "contacts", "offers",
    ]) {
      expect(HOOK, key).toContain(`${key}: rows.${key} ?? []`);
    }
    expect(HOOK).toContain("endpoints.timelineAtlas");
    expect(HOOK).toContain("locale,");
    expect(HOOK).toContain('fail("failures.searchAtlas")');
  });

  it("renders every field the engine emits and teaches the one control", () => {
    for (const field of ["region.id", "region.title", "region.count", "region.explored", "region.note", "map.total_evidence"]) {
      expect(CARD, field).toContain(field);
    }
    // A native Button is the tooltip's child here — the boxless span anchor is
    // only for Radix controls that own data-state (tabs, selects, switches).
    expect(CARD).toContain('<Hint label={t("data.atlasHint")}>');
    expect(CARD).toContain('t("data.atlasHint")');
  });

  it("resolves the new copy in both languages, purely", () => {
    const keys = [
      "data.atlasTitle", "data.atlasDescription", "data.atlasDraw", "data.atlasDrawing",
      "data.atlasTotal", "data.atlasUnexplored", "data.atlasHint", "failures.searchAtlas",
    ];
    for (const locale of ["en", "zh"] as const) {
      for (const key of keys) {
        expect(lookup(translations[locale], key), `${locale}:${key}`).toBeTruthy();
      }
    }
    for (const key of keys) {
      expect(lookup(translations.en, key)!, key).not.toMatch(/[\u4e00-\u9fff]/);
      expect(lookup(translations.zh, key)!, key).toMatch(/[\u4e00-\u9fff]/);
    }
  });
});
