"use client";

import { useLocale } from "@/lib/i18n/locale-context";
import { prepareNoteDraft } from "@/lib/interview-study";

import { KeepAsNoteButton } from "./keep-as-note-button";

/**
 * 63.2: keeps one of the report's questions-to-prepare as a knowledge-base note.
 *
 * The question is what the reader will search for before the next round, so it
 * becomes the title and the origin line stays in the body. The click is the
 * shared `KeepAsNoteButton`, the same one the study, rewrite and gap cards use.
 */
export function PrepareNoteButton({ question, origin }: { question: string; origin?: string }) {
  const { t } = useLocale();
  const draft = prepareNoteDraft(question, t("interviews.report.untitledPrepare"), origin);
  return <KeepAsNoteButton draft={draft} />;
}
