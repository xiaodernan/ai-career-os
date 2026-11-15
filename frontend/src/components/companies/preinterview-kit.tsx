"use client";

/**
 * The room you walk into (Epic 268) — the pre-interview research kit.
 *
 * The company page answers "what is this room?"; this is the reader's own
 * half — five lenses they write for themselves, kept in this browser like
 * every other keepsake, sealing enough truth to earn two questions back.
 * The questions the kit proposes are assembled from the reader's *own*
 * sentences, quoted verbatim — a launchpad, never a script. Nothing here
 * predicts the interviewer; it just makes sure the reader arrives with
 * evidence instead of vibes.
 */

import * as React from "react";
import { Check, Copy, DoorOpen, RotateCcw } from "lucide-react";
import { toast } from "sonner";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Hint } from "@/components/ui/hint";
import { useLocale } from "@/lib/i18n/locale-context";
import {
  MAX_TOTAL,
  LENS_IDS,
  READY_TOTAL,
  blankState,
  levelTotal,
  readyForSynthesis,
  readPreread,
  synthesisLenses,
  writePreread,
  type LensId,
  type PrereadLevel,
  type PrereadState,
} from "@/lib/preread";

const LENS_LABEL_KEYS: Record<LensId, { label: string; hint: string }> = {
  money: { label: "companies.prereadMoneyLabel", hint: "companies.prereadMoneyHint" },
  role: { label: "companies.prereadRoleLabel", hint: "companies.prereadRoleHint" },
  year: { label: "companies.prereadYearLabel", hint: "companies.prereadYearHint" },
  proof: { label: "companies.prereadProofLabel", hint: "companies.prereadProofHint" },
  bet: { label: "companies.prereadBetLabel", hint: "companies.prereadBetHint" },
};

const QUESTION_KEYS: Record<LensId, string> = {
  money: "companies.prereadQ_money",
  role: "companies.prereadQ_role",
  year: "companies.prereadQ_year",
  proof: "companies.prereadQ_proof",
  bet: "companies.prereadQ_bet",
};

export function PreinterviewKit({ companyId }: { companyId: string }) {
  const { t, locale } = useLocale();
  const [state, setState] = React.useState<PrereadState>(() => blankState());
  const [loaded, setLoaded] = React.useState(false);
  const [copied, setCopied] = React.useState<LensId | null>(null);

  // localStorage is read after mount, never during render — same contract every keepsake holds.
  React.useEffect(() => {
    setState(readPreread(companyId));
    setLoaded(true);
  }, [companyId]);

  const save = React.useCallback(
    (next: PrereadState) => {
      const stamped = { ...next, keptAt: new Date().toISOString() };
      setState(stamped);
      writePreread(companyId, stamped);
    },
    [companyId],
  );

  const setNote = (lens: LensId, value: string) =>
    save({ ...state, notes: { ...state.notes, [lens]: value } });

  // The level toggles are a press to set and a press to release back to zero.
  const toggleLevel = (lens: LensId, level: PrereadLevel) =>
    save({
      ...state,
      levels: { ...state.levels, [lens]: state.levels[lens] === level ? 0 : level },
    });

  const reset = () => save({ ...blankState(), keptAt: null });

  const total = levelTotal(state);
  const synthesis = readyForSynthesis(state);
  const picked = synthesis ? synthesisLenses(state, 2) : [];
  const dateFmt = (iso: string) =>
    new Date(iso).toLocaleDateString(locale === "zh" ? "zh-CN" : "en-US", {
      month: "short",
      day: "numeric",
    });

  const copyQuestion = async (lens: LensId) => {
    try {
      await navigator.clipboard.writeText(
        t(QUESTION_KEYS[lens], { note: state.notes[lens].trim() }),
      );
      setCopied(lens);
      window.setTimeout(() => setCopied(null), 1600);
    } catch {
      toast.error(t("common.clipboardBlocked"));
    }
  };

  return (
    <Card
      data-testid="preinterview-kit"
      className="col-span-full overflow-hidden border-primary/20 bg-gradient-to-br from-primary/5 via-card to-card shadow-card scroll-mt-24"
    >
      <CardHeader className="flex flex-row items-start gap-4 space-y-0">
        <div className="flex size-10 shrink-0 items-center justify-center rounded-xl border border-primary/25 bg-primary/10 text-primary">
          <DoorOpen aria-hidden className="size-5" />
        </div>
        <div className="min-w-0 flex-1">
          <CardTitle className="text-base">{t("companies.prereadTitle")}</CardTitle>
          <CardDescription>{t("companies.prereadDescription")}</CardDescription>
        </div>
        {state.keptAt && loaded && (
          <span className="shrink-0 text-2xs tabular-nums text-muted-foreground">
            {t("companies.prereadKeptAt", { date: dateFmt(state.keptAt) })}
          </span>
        )}
      </CardHeader>
      <CardContent className="space-y-4">
        {LENS_IDS.map((lens) => (
          <fieldset key={lens} className="space-y-1.5 rounded-xl border border-border/60 p-3">
            <legend className="sr-only">{t(LENS_LABEL_KEYS[lens].label)}</legend>
            <div className="flex items-baseline justify-between gap-3">
              <label htmlFor={`preread-${lens}`} className="text-sm font-medium">
                {t(LENS_LABEL_KEYS[lens].label)}
              </label>
              <div className="flex shrink-0 gap-1" role="group" aria-label={t("companies.prereadLensAria", { lens: t(LENS_LABEL_KEYS[lens].label) })}>
                {([1, 2] as const).map((level) => (
                  <Button
                    key={level}
                    type="button"
                    size="sm"
                    variant={state.levels[lens] === level ? "primary" : "outline"}
                    aria-pressed={state.levels[lens] === level}
                    className="h-7 px-2 text-2xs"
                    onClick={() => toggleLevel(lens, level)}
                  >
                    {t(level === 1 ? "companies.prereadLevelLine" : "companies.prereadLevelProof")}
                  </Button>
                ))}
              </div>
            </div>
            <p className="text-2xs leading-relaxed text-muted-foreground">{t(LENS_LABEL_KEYS[lens].hint)}</p>
            <Textarea
              id={`preread-${lens}`}
              rows={2}
              spellCheck="false"
              placeholder={t(LENS_LABEL_KEYS[lens].hint)}
              aria-label={t(LENS_LABEL_KEYS[lens].label)}
              value={loaded ? state.notes[lens] : ""}
              onChange={(event) => setNote(lens, event.target.value)}
            />
          </fieldset>
        ))}

        <div className="flex items-center justify-between gap-3 text-xs tabular-nums text-muted-foreground">
          <span>{t("companies.prereadCount", { done: total })}</span>
          <div
            className="h-1.5 w-36 overflow-hidden rounded-full bg-muted"
            role="progressbar"
            aria-valuemin={0}
            aria-valuemax={MAX_TOTAL}
            aria-valuenow={total}
            aria-label={t("companies.prereadCount", { done: total })}
          >
            <div
              className="h-full rounded-full bg-primary transition-[width]"
              style={{ width: `${Math.round((total / MAX_TOTAL) * 100)}%` }}
            />
          </div>
          {total > 0 && (
            <Hint side="left" label={t("chrome.resetHint")}>
              <Button
                variant="ghost"
                size="icon-sm"
                onClick={reset}
                aria-label={t("companies.prereadReset")}
              >
                <RotateCcw aria-hidden className="size-4" />
              </Button>
            </Hint>
          )}
        </div>

        {state && total >= READY_TOTAL && picked.length === 2 ? (
          <div className="space-y-3 border-t border-border/60 pt-4">
            <p className="text-sm font-medium">{t("companies.prereadGather")}</p>
            <p className="text-2xs text-muted-foreground">{t("companies.prereadAskThem")}</p>
            <ol className="space-y-2">
              {picked.map((lens, index) => (
                <li
                  key={lens}
                  className="flex items-start justify-between gap-3 rounded-lg border border-primary/25 bg-primary/5 p-3"
                >
                  <span className="text-sm leading-relaxed">
                    <span className="mr-2 font-serif tabular-nums text-primary">{index + 1}.</span>
                    {t(QUESTION_KEYS[lens], { note: state.notes[lens].trim() })}
                  </span>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon-sm"
                    className="shrink-0"
                    aria-label={t("common.copiedToClipboard")}
                    onClick={() => void copyQuestion(lens)}
                  >
                    {copied === lens ? <Check aria-hidden className="size-4" /> : <Copy aria-hidden className="size-4" />}
                  </Button>
                </li>
              ))}
            </ol>
          </div>
        ) : (
          <p className="text-2xs leading-relaxed text-muted-foreground">{t("companies.prereadGate")}</p>
        )}
      </CardContent>
    </Card>
  );
}
