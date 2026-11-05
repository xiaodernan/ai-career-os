"use client";

import * as React from "react";
import { Check, StickyNote } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useNoteMutations } from "@/lib/hooks/actions";
import { useLocale } from "@/lib/i18n/locale-context";
import { studyNoteDraft, type StudySource } from "@/lib/interview-study";

/**
 * 60.1: keeps one of the report's study items as a knowledge-base note.
 *
 * `POST /knowledge/notes` ingests the text it saves, so a note is not a dead
 * row: the copilot can quote it back on the next question. The button says
 * "kept" once the mutation lands and never offers a second copy of the same
 * item -- the note list is where duplicates would accumulate.
 */
export function StudyNoteButton({ item, origin }: { item: StudySource; origin?: string }) {
  const { t } = useLocale();
  const { create } = useNoteMutations();
  const [kept, setKept] = React.useState(false);
  // 60.2: the origin arrives already phrased ("from your rehearsal for ..."),
  // and rides into the note body so the advice keeps its source.
  const draft = studyNoteDraft(item, t("interviews.report.untitledNote"), origin);

  return (
    <Button
      type="button"
      variant="ghost"
      size="sm"
      className="shrink-0"
      disabled={create.isPending || kept}
      onClick={() => create.mutate(draft, { onSuccess: () => setKept(true) })}
    >
      {kept ? <Check aria-hidden /> : <StickyNote aria-hidden />}
      {kept ? t("interviews.report.noteKept") : t("interviews.report.keepAsNote")}
    </Button>
  );
}
