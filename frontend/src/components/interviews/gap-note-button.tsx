"use client";

import { useLocale } from "@/lib/i18n/locale-context";
import { gapNoteDraft } from "@/lib/interview-study";

import { KeepAsNoteButton } from "./keep-as-note-button";

/**
 * 63.1: keeps one of the report's missing concepts as a knowledge-base note.
 *
 * The gap card used to be a list of things the reader had to remember. A note is
 * ingested, so the same concept can be quoted back by the copilot -- and the
 * origin line says which rehearsal found it. The click itself is
 * `KeepAsNoteButton`, shared with the study and rewrite cards.
 */
export function GapNoteButton({ gap, origin }: { gap: string; origin?: string }) {
  const { t } = useLocale();
  const draft = gapNoteDraft(gap, t("interviews.report.untitledGap"), origin);
  return <KeepAsNoteButton draft={draft} />;
}
