"use client";

import * as React from "react";
import { Check, StickyNote } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useNoteMutations } from "@/lib/hooks/actions";
import { useLocale } from "@/lib/i18n/locale-context";
import type { NoteDraft } from "@/lib/interview-study";

/**
 * Keeps one draft as a knowledge-base note (60.1, 61.3).
 *
 * The report offers this on two kinds of advice -- a study item and a stronger
 * answer -- and both end in the same place: a POST whose server-side handler
 * ingests the text, so the note is citable evidence rather than a dead row. The
 * button owns only the part that must be identical on both: one click, one
 * request, and a "kept" state that refuses a second copy of the same item.
 */
export function KeepAsNoteButton({ draft }: { draft: NoteDraft }) {
  const { t } = useLocale();
  const { create } = useNoteMutations();
  const [kept, setKept] = React.useState(false);

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
