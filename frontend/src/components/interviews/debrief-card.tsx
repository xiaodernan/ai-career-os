"use client";

import * as React from "react";
import { PenLine, RotateCcw } from "lucide-react";
import { toast } from "sonner";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useLocale } from "@/lib/i18n/locale-context";
import {
  clearDebrief,
  debriefIsEmpty,
  loadDebrief,
  saveDebrief,
  type DebriefState,
} from "@/lib/interviews/debrief";

/**
 * The debrief (Epic 219) — the reader's own two lines on a rehearsal.
 *
 * The evaluator scores the session against its rubric; every coach's playbook
 * says the reader's own honesty matters more than any scorecard. Two fields —
 * what happened, what they'll do differently — persisted in the reader's
 * browser only, keyed by the session id. Nothing is sent anywhere, nothing is
 * graded, nothing is scored. The empty state is an invitation, not a form.
 */
export function DebriefCard({ sessionId }: { sessionId: string }) {
  const { t } = useLocale();
  const [state, setState] = React.useState<DebriefState>(() => ({ whatHappened: "", differently: "" }));
  const [hydrated, setHydrated] = React.useState(false);

  React.useEffect(() => {
    setState(loadDebrief(sessionId));
    setHydrated(true);
  }, [sessionId]);

  React.useEffect(() => {
    if (hydrated) saveDebrief(sessionId, state);
  }, [state, hydrated, sessionId]);

  const empty = debriefIsEmpty(state);

  const update = (field: keyof DebriefState) => (event: React.ChangeEvent<HTMLTextAreaElement>) => {
    setState((prev) => ({ ...prev, [field]: event.target.value }));
  };

  const reset = () => {
    clearDebrief(sessionId);
    setState({ whatHappened: "", differently: "" });
    toast.success(t("interviews.debrief.resetDone"));
  };

  const whatId = `debrief-what-${sessionId}`;
  const differentId = `debrief-different-${sessionId}`;

  return (
    <Card data-testid="debrief-card" className="border-primary/15 bg-gradient-to-br from-primary/[0.04] via-card to-card">
      <CardHeader className="flex flex-row items-start gap-4 space-y-0 pb-3">
        <div className="flex size-10 shrink-0 items-center justify-center rounded-xl border border-primary/25 bg-primary/10 text-primary">
          <PenLine aria-hidden className="size-5" />
        </div>
        <div className="min-w-0">
          <p className="text-2xs font-semibold uppercase tracking-widest text-primary">{t("interviews.debrief.eyebrow")}</p>
          <CardTitle className="mt-0.5 text-base">{t("interviews.debrief.title")}</CardTitle>
          <CardDescription>{t("interviews.debrief.hint")}</CardDescription>
        </div>
        {!empty && (
          <Button
            variant="ghost"
            size="icon-sm"
            className="ml-auto shrink-0"
            onClick={reset}
            aria-label={t("interviews.debrief.reset")}
          >
            <RotateCcw aria-hidden className="size-4" />
          </Button>
        )}
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-1.5">
          <Label htmlFor={whatId}>{t("interviews.debrief.whatHappened")}</Label>
          <Textarea
            id={whatId}
            value={state.whatHappened}
            onChange={update("whatHappened")}
            placeholder={t("interviews.debrief.whatHappenedPlaceholder")}
            rows={2}
            maxLength={4000}
            className="text-sm leading-relaxed"
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor={differentId}>{t("interviews.debrief.differently")}</Label>
          <Textarea
            id={differentId}
            value={state.differently}
            onChange={update("differently")}
            placeholder={t("interviews.debrief.differentlyPlaceholder")}
            rows={2}
            maxLength={4000}
            className="text-sm leading-relaxed"
          />
        </div>
        {!empty && (
          <p role="status" className="text-2xs text-muted-foreground">
            {t("interviews.debrief.savedLocal")}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
