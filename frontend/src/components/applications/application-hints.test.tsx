import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { lookup } from "@/lib/i18n/locale-context";
import { translations } from "@/lib/i18n/translations";

const DIALOG_KEYS = [
  "hintStage", "hintClearReminder", "hintStartRehearsal", "hintDeleteApplication",
  "hintCancelApplication", "hintSaveApplication", "hintAddApplication",
] as const;

const LETTER_KEYS = [
  "hintVersionLink", "hintWriteOne", "hintDisclosure", "hintCopy", "hintDownload",
  "hintEdit", "hintRewrite", "hintRemove", "hintTone", "hintLength",
  "hintCancelEdit", "hintSaveEdit",
] as const;

const PACKET_KEYS = [
  "hintOpenResume", "hintOpenJd", "hintOpenMatch", "hintOpenRehearsals",
] as const;

function source(path: string): string {
  return readFileSync(new URL(path, import.meta.url), "utf8");
}

const dialog = source("./application-dialog.tsx");
const letters = source("./application-letters.tsx");
const packet = source("./application-packet.tsx");

describe("shared application teaching hints", () => {
  it("defines every dialog, letter and packet consequence in both languages", () => {
    for (const locale of ["en", "zh"] as const) {
      for (const key of DIALOG_KEYS) {
        expect(lookup(translations[locale], `applications.dialog.${key}`), `${locale}: ${key}`).toBeTruthy();
      }
      for (const key of LETTER_KEYS) {
        expect(lookup(translations[locale], `applications.dialog.${key}`), `${locale}: ${key}`).toBeTruthy();
      }
      for (const key of PACKET_KEYS) {
        expect(lookup(translations[locale], `applications.dialog.packet.${key}`), `${locale}: ${key}`).toBeTruthy();
      }
    }
  });

  it("wires all seven dialog controls and keeps Select and loading state independent", () => {
    for (const key of DIALOG_KEYS) expect(dialog).toContain(`applications.dialog.${key}`);
    expect(dialog).toContain('<Hint anchor="span" label={t("applications.dialog.hintStage")}>');
    expect(dialog).toContain('<Hint anchor="span" label={t("applications.dialog.hintStartRehearsal")}>');
    expect(dialog).toContain('anchor="span"\n                label={t(editing ? "applications.dialog.hintSaveApplication"');
  });

  it("keeps the letter disclosure a direct summary and wraps stateful editor controls", () => {
    for (const key of LETTER_KEYS) expect(letters).toContain(`applications.dialog.${key}`);
    expect(letters).toMatch(/<Hint label=\{t\("applications\.dialog\.hintDisclosure"\)\}>\s*<summary/);
    expect(letters).toContain('<Hint anchor="span" label={t("applications.dialog.hintTone")}>');
    expect(letters).toContain('<Hint anchor="span" label={t("applications.dialog.hintLength")}>');
    expect(letters).toContain('<Hint anchor="span" label={t("applications.dialog.hintSaveEdit")}>');
  });

  it("teaches exactly the four packet rows that really open another screen", () => {
    for (const key of PACKET_KEYS) expect(packet).toContain(`applications.dialog.packet.${key}`);
    expect(packet.match(/hint: "applications\.dialog\.packet\.hintOpen/g)).toHaveLength(4);
    expect(packet).toContain('<Hint label={t(row.hint)}>');
  });
});
