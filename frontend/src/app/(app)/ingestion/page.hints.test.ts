import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { lookup } from "@/lib/i18n/locale-context";
import { translations } from "@/lib/i18n/translations";

/**
 * Epic 435 — the last zero-teaching surfaces on the main screens. Ingestion is a
 * front door whose fourteen controls included destructive ones (delete feed, apply
 * plan, toggle sweep); monitoring, analysis, growth, ceremony, notifications and
 * activity each had a handful of untaught buttons. This pins every new hint to both
 * its source file and to both language tables.
 */
const INGESTION = [
  "ingestion.hintFeedContent",
  "ingestion.hintParse",
  "ingestion.hintBuildPlan",
  "ingestion.hintDeduplicate",
  "ingestion.hintFreshnessSweep",
  "ingestion.hintFeedName",
  "ingestion.hintFeedUrl",
  "ingestion.hintFeedSource",
  "ingestion.hintAddFeed",
  "ingestion.hintToggleFeed",
  "ingestion.hintRunNow",
  "ingestion.hintDeleteFeed",
  "ingestion.hintApplyPlan",
  "ingestion.hintViewPlan",
] as const;

const OTHER_KEYS = [
  "monitoring.hintRefresh",
  "analysis.hintRefresh",
  "analysis.hintCompose",
  "growth.hintTargetRole",
  "growth.hintLocation",
  "growth.hintAnalyze",
  "growthEngines.hintTargetRole",
  "growthEngines.hintLocation",
  "ceremony.hintReviewDownload",
  "ceremony.hintLegacyOpen",
  "notifications.hintMarkAllRead",
  "notifications.hintClearRead",
  "notifications.hintFilterAll",
  "notifications.hintFilterKind",
  "notifications.hintFilterUnread",
  "notifications.hintSnoozeReminder",
  "notifications.hintClearReminder",
  "notifications.hintOpen",
  "activity.hintTrace",
] as const;

const ALL_KEYS = [...INGESTION, ...OTHER_KEYS];

function source(relative: string): string {
  return readFileSync(resolve(__dirname, relative), "utf8");
}

describe("Remaining teaching hints (Epic 435)", () => {
  const files = [
    "./page.tsx",
    "../../../components/ingestion/scheduled-feeds-panel.tsx",
    "../monitoring/page.tsx",
    "../analysis/page.tsx",
    "../growth/page.tsx",
    "../../../components/growth/growth-engines-panel.tsx",
    "../../../components/ceremony/year-in-review-card.tsx",
    "../../../components/ceremony/legacy-card.tsx",
    "../notifications/page.tsx",
    "../activity/page.tsx",
  ].map(source);
  const allSource = files.join("\n");

  it("references every new hint key from a source file", () => {
    for (const key of ALL_KEYS) {
      expect(allSource, key).toContain(`"${key}"`);
    }
  });

  it("uses the boxless span anchor on stateful and as-child controls", () => {
    // Textarea/Input/Select/Switch/TabsTriggers own their state, and as-child links
    // carry their own props; a wrapper tooltip writing data-state over them corrupts
    // the control. The span anchor keeps the two independent.
    for (const key of [
      "ingestion.hintFeedContent",
      "ingestion.hintFeedName",
      "ingestion.hintFeedUrl",
      "ingestion.hintFeedSource",
      "ingestion.hintToggleFeed",
      "growth.hintTargetRole",
      "growth.hintLocation",
      "growthEngines.hintTargetRole",
      "growthEngines.hintLocation",
      "notifications.hintFilterAll",
      "notifications.hintFilterKind",
      "notifications.hintFilterUnread",
      "notifications.hintOpen",
      "activity.hintTrace",
    ]) {
      expect(allSource, key).toContain(`anchor="span" label={t("${key}")}`);
    }
  });

  it("resolves all hints in both languages", () => {
    for (const locale of ["en", "zh"] as const) {
      for (const key of ALL_KEYS) {
        const value = lookup(translations[locale], key);
        expect(value, `${locale}:${key}`).toBeTruthy();
        // Each hint names a consequence — a full sentence, not a label stub.
        expect(value!.length, `${locale}:${key}`).toBeGreaterThan(8);
      }
    }
  });

  it("keeps the two language tables pure", () => {
    for (const key of ALL_KEYS) {
      const en = lookup(translations.en, key)!;
      const zh = lookup(translations.zh, key)!;
      // No Han character in the English table, no English sentence in the Chinese one.
      expect(en, key).not.toMatch(/[\u4e00-\u9fff]/);
      expect(zh, key).not.toMatch(/\b(the|this|and|with|that|reads|your)\b/i);
    }
  });
});
