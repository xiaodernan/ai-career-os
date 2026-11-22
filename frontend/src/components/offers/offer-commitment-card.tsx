"use client";

import * as React from "react";
import { RotateCcw, PenLine } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Hint } from "@/components/ui/hint";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { useLocale } from "@/lib/i18n/locale-context";
import {
  clearCommitment,
  loadCommitment,
  saveCommitment,
  COMMITMENT_MAX_LENGTH,
} from "@/lib/commitment";

/**
 * The week's one line (Epic 228) — the sentence the reader will say out loud.
 *
 * The whole search is open-ended, and open-ended things exhaust people; one
 * line a week narrows it. The current ISO week is the key, so the card rotates
 * itself forward on Monday; last week's line is archived by the calendar, not
 * surfaced as a reproach. In the pocket for the export path too.
 */
export function OfferCommitmentCard() {
  const { t } = useLocale();
  const [state, setState] = React.useState(() => loadCommitment(
    typeof window === "undefined" ? null : window.localStorage
  ));
  const [draft, setDraft] = React.useState("");
  const [saved, setSaved] = React.useState(false);

  React.useEffect(() => {
    setDraft(state.text);
  }, [state.week, state.text]);

  const dirty = draft.trim() !== state.text;
  const filled = state.text.trim().length > 0;

  const save = () => {
    const next = saveCommitment(draft);
    setState(next);
    setDraft(next.text);
    setSaved(true);
  };

  const reset = () => {
    clearCommitment();
    setState((prev) => ({ ...prev, text: "" }));
    setDraft("");
    setSaved(false);
  };

  return (
    <Card data-testid="commitment-card" className="border-primary/15 shadow-card">
      <CardHeader className="flex flex-row items-start gap-4 space-y-0">
        <div className="flex size-10 shrink-0 items-center justify-center rounded-xl border border-primary/25 bg-primary/10 text-primary">
          <PenLine aria-hidden className="size-5" />
        </div>
        <div className="min-w-0">
          <CardTitle className="text-base">{t("offers.commitmentTitle")}</CardTitle>
          <CardDescription>{t("offers.commitmentDescription")}</CardDescription>
        </div>
        {filled && (
                    <Hint side="left" label={t("chrome.resetHint")}>
<Button variant="ghost" size="icon-sm" className="ml-auto shrink-0" onClick={reset} aria-label={t("offers.commitmentReset")} title={t("offers.commitmentReset")}>
            <RotateCcw aria-hidden className="size-4" />
          </Button>
          </Hint>
        )}
      </CardHeader>
      <CardContent className="space-y-3">
        {filled && (
          <blockquote className="rounded-xl border-l-2 border-primary/40 bg-primary/[0.06] px-4 py-3 text-sm leading-relaxed text-foreground/90">
            {state.text}
          </blockquote>
        )}
        <div className="space-y-1.5">
          <Label htmlFor="commitment-line">
            {t("offers.commitmentLabel", { week: state.week })}
          </Label>
          <Textarea
            id="commitment-line"
            value={draft}
            onChange={(event) => {
              setDraft(event.target.value);
              setSaved(false);
            }}
            placeholder={t("offers.commitmentPlaceholder")}
            rows={2}
            maxLength={COMMITMENT_MAX_LENGTH}
            aria-describedby="commitment-count"
          />
          <div className="flex items-center justify-between gap-2 text-2xs text-muted-foreground">
            <span id="commitment-count" className="tabular-nums">
              {draft.length} / {COMMITMENT_MAX_LENGTH}
            </span>
            {saved && <span className="text-success">{t("offers.commitmentSaved")}</span>}
          </div>
          <Button variant="ai" size="sm" onClick={save} disabled={!dirty || draft.trim().length === 0}>
            {t("offers.commitmentSave")}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
