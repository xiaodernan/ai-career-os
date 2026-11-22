"use client";

import * as React from "react";
import { CalendarClock, LockKeyhole, MailPlus, RefreshCw, Trash2, Unlock } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { SectionHeading } from "@/components/common/export-buttons";
import { useLocale } from "@/lib/i18n/locale-context";
import { formatDate } from "@/lib/format";
import { useKnowledgeNotes } from "@/lib/hooks/resources";
import { useNoteMutations } from "@/lib/hooks/actions";
import {
  CAPSULE_TAG,
  addDays,
  buildCapsuleTags,
  localDateKey,
  readCapsules,
} from "@/lib/time-capsule";
import { capsulePromptKey } from "@/lib/capsule-prompts";

/**
 * Epic 384 — the sealed letter. A capsule is an ordinary note with a dated tag;
 * the card renders a sealed body as an envelope, never as prose, until its date
 * arrives. No new table, no new endpoint, and the letter travels in the reader's
 * own export like every other note.
 */
export function TimeCapsuleCard() {
  const { t, locale } = useLocale();
  const query = useKnowledgeNotes({ tag: CAPSULE_TAG, size: 50 });
  const notes = useNoteMutations();
  const [writing, setWriting] = React.useState(false);
  const [content, setContent] = React.useState("");
  const [revealDate, setRevealDate] = React.useState(() => addDays(90));
  const [promptOffset, setPromptOffset] = React.useState(0);
  const [error, setError] = React.useState<string | null>(null);

  const today = localDateKey();
  const capsules = readCapsules(query.data?.items, today);
  const promptKey = capsulePromptKey(new Date(), promptOffset);

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    if (!content.trim()) {
      setError(t("timeline.capsuleNeedContent"));
      return;
    }
    if (revealDate <= today) {
      setError(t("timeline.capsuleNeedFuture"));
      return;
    }
    setError(null);
    notes.create.mutate(
      {
        // A system note needs no title; the dated tag carries the only metadata the
        // card reads, and an empty title keeps the stored row language-neutral.
        title: "",
        content: content.trim(),
        tags: buildCapsuleTags(revealDate),
      },
      {
        onSuccess: () => {
          setWriting(false);
          setContent("");
          setRevealDate(addDays(90));
          setPromptOffset(0);
        },
      },
    );
  };

  return (
    <Card className="border-border/70 shadow-card">
      <CardHeader className="pb-3">
        <SectionHeading
          eyebrow={t("eyebrows.timeCapsule")}
          icon={<MailPlus className="size-4" aria-hidden />}
          title={t("timeline.capsuleTitle")}
          description={t("timeline.capsuleDescription")}
        />
      </CardHeader>
      <CardContent className="space-y-4">
        {!writing ? (
          <Button variant="outline" size="sm" className="gap-2" onClick={() => setWriting(true)}>
            <MailPlus aria-hidden className="size-4" />
            {t("timeline.capsuleWrite")}
          </Button>
        ) : (
          <form onSubmit={submit} className="space-y-3 rounded-xl border border-border/60 bg-card/60 p-4">
            <div className="rounded-lg border border-border/50 bg-muted/30 p-3">
              <p className="text-2xs font-medium uppercase tracking-wide text-muted-foreground">
                {t("timeline.capsulePromptLabel")}
              </p>
              <p className="mt-1 text-sm italic leading-relaxed text-foreground/80">{t(promptKey)}</p>
              <Button
                type="button"
                variant="ghost"
                size="xs"
                className="mt-1 gap-1 text-muted-foreground"
                onClick={() => setPromptOffset((offset) => offset + 1)}
              >
                <RefreshCw aria-hidden className="size-3" />
                {t("timeline.capsulePromptNext")}
              </Button>
            </div>
            <label className="block text-xs font-medium text-muted-foreground" htmlFor="capsule-body">
              {t("timeline.capsuleBodyLabel")}
            </label>
            <textarea
              id="capsule-body"
              value={content}
              onChange={(event) => setContent(event.target.value)}
              placeholder={t("timeline.capsulePlaceholder")}
              rows={5}
              maxLength={8000}
              className="w-full resize-y rounded-lg border border-border/70 bg-background/70 p-3 text-sm leading-relaxed outline-none focus-visible:ring-2 focus-visible:ring-primary/50"
            />
            <div className="flex flex-wrap items-end justify-between gap-3">
              <label className="flex flex-col gap-1 text-xs font-medium text-muted-foreground">
                {t("timeline.capsuleDateLabel")}
                <input
                  type="date"
                  value={revealDate}
                  min={addDays(1)}
                  onChange={(event) => setRevealDate(event.target.value)}
                  className="rounded-lg border border-border/70 bg-background/70 px-3 py-1.5 text-sm text-foreground outline-none focus-visible:ring-2 focus-visible:ring-primary/50"
                />
              </label>
              <div className="flex flex-wrap gap-2">
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setWriting(false);
                    setError(null);
                  }}
                >
                  {t("timeline.capsuleCancel")}
                </Button>
                <Button type="submit" variant="ai" size="sm" disabled={notes.create.isPending}>
                  <LockKeyhole aria-hidden className="size-3.5" />
                  {notes.create.isPending ? t("timeline.capsuleSealing") : t("timeline.capsuleSeal")}
                </Button>
              </div>
            </div>
            {error && <p className="text-xs leading-relaxed text-warning">{error}</p>}
          </form>
        )}

        {query.isError ? (
          <p className="text-sm leading-relaxed text-muted-foreground">{t("timeline.capsuleUnavailable")}</p>
        ) : capsules.length === 0 ? (
          <p className="text-sm leading-relaxed text-muted-foreground">{t("timeline.capsuleEmpty")}</p>
        ) : (
          <ol className="space-y-2">
            {capsules.map((capsule) => (
              <li key={capsule.note.id} className="rounded-xl border border-border/60 bg-card/50 p-4">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div className="flex min-w-0 flex-wrap items-center gap-2">
                    {capsule.sealed ? (
                      <LockKeyhole aria-hidden className="size-4 shrink-0 text-primary" />
                    ) : (
                      <Unlock aria-hidden className="size-4 shrink-0 text-primary" />
                    )}
                    <span className="inline-flex items-center gap-1 font-mono text-xs tabular-nums text-muted-foreground">
                      <CalendarClock aria-hidden className="size-3.5" />
                      {formatDate(capsule.revealDate, locale)}
                    </span>
                    <Badge variant={capsule.sealed ? "secondary" : "outline"} className="text-2xs">
                      {capsule.sealed ? t("timeline.capsuleSealed") : t("timeline.capsuleOpen")}
                    </Badge>
                  </div>
                  <Button
                    variant="ghost"
                    size="xs"
                    className="shrink-0 text-muted-foreground hover:text-warning"
                    aria-label={t("timeline.capsuleDelete")}
                    title={t("timeline.capsuleDelete")}
                    disabled={notes.remove.isPending}
                    onClick={() => notes.remove.mutate(capsule.note.id)}
                  >
                    <Trash2 aria-hidden className="size-3.5" />
                  </Button>
                </div>
                {capsule.sealed ? (
                  <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                    {t("timeline.capsuleSealedUntil", {
                      days: capsule.days,
                      date: formatDate(capsule.revealDate, locale),
                    })}
                  </p>
                ) : (
                  <p className="mt-2 whitespace-pre-wrap break-words text-sm leading-relaxed text-foreground/90">
                    {capsule.note.content}
                  </p>
                )}
              </li>
            ))}
          </ol>
        )}
      </CardContent>
    </Card>
  );
}
