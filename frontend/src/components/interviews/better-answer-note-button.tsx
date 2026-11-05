"use client";

import { useLocale } from "@/lib/i18n/locale-context";
import { betterAnswerNoteDraft } from "@/lib/interview-study";

import { KeepAsNoteButton } from "./keep-as-note-button";

/**
 * 61.3: keeps one of the report's stronger answers as a knowledge-base note.
 *
 * A model answer is the other half of "what should I have said": the study card
 * says what to read, this says how it sounds. Keeping it makes that sentence
 * retrievable -- the copilot can quote the reader's own rehearsal when the same
 * question comes up again -- and the question becomes the note's title.
 */
export function BetterAnswerNoteButton({
  item,
  origin,
}: {
  item: { question?: string; answer: string };
  origin?: string;
}) {
  const { t } = useLocale();
  const draft = betterAnswerNoteDraft(item, t("interviews.report.modelAnswerTitle"), origin);
  return <KeepAsNoteButton draft={draft} />;
}
