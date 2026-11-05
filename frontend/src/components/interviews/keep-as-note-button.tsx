"use client";

import * as React from "react";
import Link from "next/link";
import { ArrowUpRight, Check, StickyNote } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useNoteMutations } from "@/lib/hooks/actions";
import { useLocale } from "@/lib/i18n/locale-context";
import { noteHref } from "@/lib/note-tags";
import type { NoteDraft } from "@/lib/interview-study";

/**
 * 69.1: what the button becomes once the note exists -- the way to it.
 *
 * "Kept in knowledge" said what happened and left the reader to go find it.
 * The kept state is a door now, and it is its own component so that promise can
 * be read without a browser: the link opens the notes carrying the draft's own
 * kind tag, the narrowing the reader would otherwise do by hand.
 */
export function KeptNoteLink({ tags }: { tags: readonly string[] }) {
  const { t } = useLocale();
  return (
    <Button asChild variant="ghost" size="sm" className="shrink-0">
      <Link href={noteHref(tags)}>
        <Check aria-hidden />
        {t("interviews.report.noteKeptOpen")}
        <ArrowUpRight aria-hidden />
      </Link>
    </Button>
  );
}

/**
 * Keeps one draft as a knowledge-base note (60.1, 61.3).
 *
 * The report offers this on four kinds of advice -- a study item, a stronger
 * answer, a gap and a question to prepare -- and all of them end in the same
 * place: a POST whose server-side handler ingests the text, so the note is
 * citable evidence rather than a dead row. The button owns only the part that
 * must be identical on all four: one click, one request, and a "kept" state
 * that refuses a second copy of the same item.
 */
export function KeepAsNoteButton({ draft }: { draft: NoteDraft }) {
  const { t } = useLocale();
  const { create } = useNoteMutations();
  const [kept, setKept] = React.useState(false);

  if (kept) return <KeptNoteLink tags={draft.tags} />;

  return (
    <Button
      type="button"
      variant="ghost"
      size="sm"
      className="shrink-0"
      disabled={create.isPending}
      onClick={() => create.mutate(draft, { onSuccess: () => setKept(true) })}
    >
      <StickyNote aria-hidden />
      {t("interviews.report.keepAsNote")}
    </Button>
  );
}
