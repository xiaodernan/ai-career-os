"use client";

import * as React from "react";
import { Check, MailOpen, RotateCcw } from "lucide-react";
import { cn } from "@/lib/utils";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Hint } from "@/components/ui/hint";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { useLocale } from "@/lib/i18n/locale-context";
import {
  NOT_YET_DOORS,
  NOT_YET_MAX_LENGTH,
  clearNotYet,
  loadNotYet,
  saveNotYet,
} from "@/lib/replies/not-yet";

/**
 * The not-yet letter (Epic 237) — the door nobody writes down.
 *
 * Every recruiter's no is a letter a real person read yours and then wrote.
 * Three shapes they actually write, each with the honest decode beside it.
 * Not a game, not a score: one kept sentence, the same contract the debrief
 * and the ledger use. Local-only, nothing here is sent anywhere.
 */
export function NotYetCard() {
  const { t } = useLocale();
  const [sentence, setSentence] = React.useState(() =>
    loadNotYet(typeof window === "undefined" ? null : window.localStorage).sentence
  );
  const [open, setOpen] = React.useState<string | null>(null);

  const save = (event: React.ChangeEvent<HTMLTextAreaElement>) => {
    setSentence(event.target.value);
    saveNotYet(event.target.value);
  };

  const reset = () => {
    clearNotYet();
    setSentence("");
  };

  return (
    <Card
      data-testid="not-yet-card"
      className="overflow-hidden border-border/70 bg-gradient-to-br from-muted/40 via-card to-card shadow-card print:break-inside-avoid"
    >
      <CardHeader className="flex flex-row items-start gap-4 space-y-0">
        <div className="flex size-10 shrink-0 items-center justify-center rounded-xl border border-border/70 bg-muted/60 text-muted-foreground">
          <MailOpen aria-hidden className="size-5" />
        </div>
        <div className="min-w-0">
          <CardTitle className="text-base">{t("replies.notYetTitle")}</CardTitle>
          <CardDescription>{t("replies.notYetDescription")}</CardDescription>
        </div>
        {sentence.trim() !== "" && (
                    <Hint side="left" label={t("chrome.resetHint")}>
<Button variant="ghost" size="icon-sm" className="ml-auto shrink-0" onClick={reset} aria-label={t("replies.notYetReset")}>
            <RotateCcw aria-hidden className="size-4" />
          </Button>
          </Hint>
        )}
      </CardHeader>
      <CardContent className="space-y-4">
        <ol className="grid gap-2 md:grid-cols-3">
          {NOT_YET_DOORS.map((door) => {
            const expanded = open === door.id;
            return (
              <li key={door.id} className="min-w-0">
                <button
                  type="button"
                  aria-expanded={expanded}
                  aria-controls={`not-yet-${door.id}`}
                  onClick={() => setOpen((current) => (current === door.id ? null : door.id))}
                  className={cn(
                    "flex h-full w-full flex-col rounded-xl border p-3 text-left transition-colors duration-150 focus-visible:ring-[3px] focus-visible:ring-ring/30",
                    expanded ? "border-primary/30 bg-primary/[0.06]" : "border-border/60 bg-background/40 hover:border-border"
                  )}
                >
                  <span className="text-2xs font-semibold uppercase tracking-widest text-muted-foreground">
                    {t(`replies.notYetDoor_${door.id}_label`)}
                  </span>
                  <span className="mt-2 text-sm leading-snug">{t(`replies.notYetDoor_${door.id}_quote`)}</span>
                </button>
                {expanded && (
                  <div id={`not-yet-${door.id}`} className="mt-2 space-y-2 rounded-xl border border-primary/15 bg-primary/[0.04] p-3 text-xs leading-relaxed">
                    <p className="text-foreground/90">{t(`replies.notYetDoor_${door.id}_decode`)}</p>
                    <p className="text-muted-foreground">{t(`replies.notYetDoor_${door.id}_keep`)}</p>
                  </div>
                )}
              </li>
            );
          })}
        </ol>
        <div className="space-y-1.5">
          <Label htmlFor="not-yet-keep">{t("replies.notYetKeepTitle")}</Label>
          <p className="text-2xs text-muted-foreground">{t("replies.notYetKeepDescription")}</p>
          <Textarea
            id="not-yet-keep"
            value={sentence}
            onChange={save}
            placeholder={t("replies.notYetKeepPlaceholder")}
            rows={2}
            maxLength={NOT_YET_MAX_LENGTH}
            className="text-sm leading-relaxed"
          />
          {sentence.trim() !== "" && (
            <p className="inline-flex items-center gap-1.5 text-2xs text-success">
              <Check aria-hidden className="size-3" />
              {t("replies.notYetKept")}
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
