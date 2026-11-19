"use client";

import * as React from "react";
import { Copy, Check, Mail } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Hint } from "@/components/ui/hint";
import { useLocale } from "@/lib/i18n/locale-context";
import { useInterviewThankYouLetter } from "@/lib/hooks/actions";

/**
 * Epic 336 — the thank-you letter the reader sends after the interview.
 *
 * Ask-first: the button carries a Hint, the writer is not called on mount, and the card
 * renders exactly what the interview produced — nothing invented, no "hi how was it" boilerplate.
 */
export function InterviewThankYouLetter({ sessionId }: { sessionId: string | null }) {
  const { t, locale } = useLocale();
  const letter = useInterviewThankYouLetter(sessionId ?? "");
  const [text, setText] = React.useState<string | null>(null);
  const [silent, setSilent] = React.useState(false);
  const [copied, setCopied] = React.useState(false);

  const copy = async () => {
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      // clipboard is not the product's promise — the letter stands on screen
    }
  };

  return (
    <div className="mt-3 rounded-lg border border-border/50 bg-muted/20 p-3">
      <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
        {t("interviews.thankYouLetter.eyebrow")}
      </p>
      {text ? (
        <>
          <p className="mt-1 whitespace-pre-wrap text-sm leading-relaxed text-foreground/90">{text}</p>
          <Button variant="ghost" size="sm" className="mt-2" onClick={() => void copy()}>
            {copied ? <Check aria-hidden /> : <Copy aria-hidden />}
            {copied ? t("interviews.thankYouLetter.copied") : t("interviews.thankYouLetter.copy")}
          </Button>
        </>
      ) : silent ? (
        <p className="mt-1 text-xs text-muted-foreground">{t("interviews.thankYouLetter.silent")}</p>
      ) : (
        <>
          <p className="mt-1 text-xs text-muted-foreground">{t("interviews.thankYouLetter.hint")}</p>
          <Hint label={t("interviews.thankYouLetter.hint")}>
            <Button
              variant="outline"
              size="sm"
              className="mt-2"
              loading={letter.isPending}
              onClick={() =>
                sessionId &&
                letter.mutate(undefined, {
                  onSuccess: (out) => {
                    if (out) {
                      setText(out);
                    } else {
                      setSilent(true);
                    }
                  },
                })
              }
            >
              <Mail aria-hidden />
              {t("interviews.thankYouLetter.button")}
            </Button>
          </Hint>
        </>
      )}
    </div>
  );
}
