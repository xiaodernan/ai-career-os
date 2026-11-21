"use client";

import * as React from "react";
import { Sparkles, CheckCircle2, AlertCircle, WandSparkles } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { useStoryForge } from "@/lib/hooks/growth";
import { useLocale } from "@/lib/i18n/locale-context";
import type { StoryForgeResult } from "@/lib/api/types";

/**
 * Epic 274 — the LLM story forge, embedded where the reader keeps interview notes.
 *
 * The engine runs a traced StateGraph (write → challenge → revise → verify): the
 * model writes a STAR story, plays a skeptical panel that names the weak spots,
 * revises using only the note, and a deterministic verifier strikes any figure
 * the note never carried. The card shows the story, the honest follow-ups the
 * reader still has to answer, and any fields that were cleared for fabrication.
 * Every word here comes from the locale table — no English literals in the DOM.
 */
export function StoryForgeCard({ seed = "" }: { seed?: string }) {
  const { t, locale } = useLocale();
  const forge = useStoryForge();
  const [note, setNote] = React.useState(seed);

  // A note handed in from a kept study note should be editable, not frozen.
  React.useEffect(() => setNote(seed), [seed]);

  const out: StoryForgeResult | null = forge.data ?? null;
  const story = out?.story;
  const fields = [
    { key: "situation", label: t("storyForge.situation") },
    { key: "task", label: t("storyForge.task") },
    { key: "action", label: t("storyForge.actionField") },
    { key: "result", label: t("storyForge.resultLabel") },
  ] as const;

  const run = () => {
    const trimmed = note.trim();
    if (trimmed.length < 10) return;
    forge.mutate({ rawNote: trimmed, locale });
  };

  return (
    <Card className="border-primary/20 shadow-card">
      <CardHeader className="gap-1.5">
        <CardTitle className="flex items-center gap-2 text-base">
          <WandSparkles className="size-4 text-primary" aria-hidden />
          {t("storyForge.title")}
        </CardTitle>
        <CardDescription>{t("storyForge.description")}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="story-forge-note">{t("storyForge.label")}</Label>
          <Textarea
            id="story-forge-note"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder={t("storyForge.placeholder")}
            rows={5}
            maxLength={12000}
          />
          <Button
            type="button"
            variant="ai"
            size="sm"
            onClick={run}
            disabled={note.trim().length < 10 || forge.isPending}
            aria-label={t("storyForge.action")}
            title={t("storyForge.action")}
          >
            <Sparkles aria-hidden className="size-4" />
            {forge.isPending ? t("storyForge.working") : t("storyForge.action")}
          </Button>
        </div>

        {out && (
          <div className="space-y-3 border-t border-border/50 pt-3">
            <p className="flex items-center gap-2 text-sm font-medium">
              {out.complete ? (
                <CheckCircle2 aria-hidden className="size-4 text-success" />
              ) : (
                <AlertCircle aria-hidden className="size-4 text-warning" />
              )}
              {t(out.complete ? "storyForge.complete" : "storyForge.incomplete")}
            </p>

            <div className="space-y-2">
              <p className="text-2xs font-semibold uppercase tracking-widest text-muted-foreground">
                {t("storyForge.storyTitle")}
              </p>
              {fields.map((f) => {
                const value = story?.[f.key];
                if (!value) return null;
                return (
                  <div key={f.key} className="rounded-lg border border-border/60 bg-muted/30 px-3 py-2">
                    <p className="text-2xs font-semibold text-primary">{f.label}</p>
                    <p className="mt-0.5 text-sm leading-relaxed">{value}</p>
                  </div>
                );
              })}
              {!story || fields.every((f) => !story[f.key]) ? (
                <p className="text-sm text-muted-foreground">{t("storyForge.emptyStory")}</p>
              ) : null}
            </div>

            {Boolean(out.open?.length) && (
              <div className="space-y-1.5">
                <p className="text-2xs font-semibold uppercase tracking-widest text-muted-foreground">
                  {t("storyForge.followupsTitle")}
                </p>
                <ul className="space-y-1">
                  {out.open?.map((q, i) => (
                    <li key={i} className="flex gap-2 text-sm leading-relaxed">
                      <Badge variant="outline" className="shrink-0 font-normal">{i + 1}</Badge>
                      <span>{q.question}</span>
                    </li>
                  ))}
                </ul>
                <p className="text-2xs text-muted-foreground">{t("storyForge.followupsHint")}</p>
              </div>
            )}

            {Boolean(out.struck_fields?.length) && (
              <div className="space-y-1">
                <p className="text-2xs font-semibold uppercase tracking-widest text-destructive">
                  {t("storyForge.struckTitle")}
                </p>
                <p className="text-sm leading-relaxed">
                  {out.struck_fields?.join(", ")} — {t("storyForge.struckHint")}
                </p>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
