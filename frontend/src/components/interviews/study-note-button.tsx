"use client";

import { useLocale } from "@/lib/i18n/locale-context";
import { studyNoteDraft, type StudySource } from "@/lib/interview-study";

import { KeepAsNoteButton } from "./keep-as-note-button";

/**
 * 60.1: keeps one of the report's study items as a knowledge-base note.
 *
 * The draft -- topic as title, reason and resource as body, the origin line from
 * 60.2 -- is this component's whole job. The click, the pending state and the
 * "kept" latch belong to `KeepAsNoteButton`, which 61.3's rewrite cards share,
 * so there is one copy of the behaviour rather than one per kind of advice.
 */
export function StudyNoteButton({ item, origin }: { item: StudySource; origin?: string }) {
  const { t } = useLocale();
  const draft = studyNoteDraft(item, t("interviews.report.untitledNote"), origin);
  return <KeepAsNoteButton draft={draft} />;
}
