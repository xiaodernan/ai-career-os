"use client";

import * as React from "react";
import Link from "next/link";
import { Compass } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Hint } from "@/components/ui/hint";
import { useLocale } from "@/lib/i18n/locale-context";
import { useApplications, useInterviewSessions } from "@/lib/hooks/resources";
import { nextFrontier } from "@/lib/next-frontier";

/**
 * The one direction the world is pointing (Epic 369).
 *
 * Brief VI asks for a world that feels endless AND for enough guidance that a reader never
 * feels lost -- the same requirement from two sides. The nine quests teach the map; this
 * card says where THIS reader is. It reads the two ledgers that already exist (the board and
 * the rehearsal history), folds them through the pure rule in `lib/next-frontier.ts`, and
 * names the single next thing worth doing with the reason it chose that one.
 *
 * The rules are ordered by what costs the reader most to leave undone: a rehearsal left
 * half-finished outranks a resume to polish, because a door that closes while you are not
 * looking is not the same as one that stays open. When nothing fires the card says the
 * honest thing -- the ledger says nothing is waiting -- rather than inventing an errand.
 */
const STAGES_THE_READER_OWNS = new Set([
  "applied",
  "screening",
  "interview",
  "take_home",
  "offer",
]);

export function FrontierCard() {
  const { t } = useLocale();
  // The two ledgers this card reads, and nothing else: the board says what is waiting on the
  // reader, the rehearsal history says what was left half-done.
  const applications = useApplications({ size: 50 });
  const rehearsals = useInterviewSessions({ size: 50 });

  const frontier = React.useMemo(() => {
    const rows = applications.data?.items ?? [];
    const sessions = rehearsals.data?.items ?? [];
    // A rehearsal that started and never finished is the one thing a reader most regrets
    // leaving: the report it would have produced is the whole point of taking it.
    // `active` and `paused` are the two states the backend spells for "still open".
    // The first browser probe of this card measured `active`, and a rule written
    // against a vocabulary the backend does not speak is a rule that never fires --
    // the card would have stayed silent forever while looking correct.
    const openRehearsals = sessions.filter(
      (session) => session.status === "active" || session.status === "paused"
    ).length;
    const awaitingReader = rows.filter(
      (row) => STAGES_THE_READER_OWNS.has(row.status ?? "")
    ).length;
    return nextFrontier({ openRehearsals, applicationsAwaitingReader: awaitingReader });
  }, [applications.data, rehearsals.data]);

  // Silence is a real answer: a reader with nothing waiting should not be handed an errand.
  if (!frontier) return null;

  return (
    <Card data-testid="frontier-card" className="border-primary/15 shadow-card">
      <CardContent className="flex flex-wrap items-center gap-4 p-5">
        <span className="flex size-10 shrink-0 items-center justify-center rounded-xl border border-primary/25 bg-primary/10 text-primary">
          <Compass aria-hidden className="size-5" />
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-2xs font-semibold uppercase tracking-widest text-primary">
            {t("frontier.eyebrow")}
          </p>
          <p className="mt-1 text-sm font-medium">{t(frontier.titleKey, frontier.vars)}</p>
          <p className="mt-0.5 text-xs leading-relaxed text-muted-foreground">
            {t(frontier.bodyKey, frontier.vars)}
          </p>
        </div>
        <Hint label={t(frontier.ctaKey, frontier.vars)}>
          <Button asChild size="sm" variant="ai">
            <Link href={frontier.href}>{t(frontier.ctaKey, frontier.vars)}</Link>
          </Button>
        </Hint>
      </CardContent>
    </Card>
  );
}
