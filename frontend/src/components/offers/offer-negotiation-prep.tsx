"use client";

import * as React from "react";
import { Copy, Check, ClipboardList } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Hint } from "@/components/ui/hint";
import { useLocale } from "@/lib/i18n/locale-context";
import { useNegotiationPrep } from "@/lib/hooks/offers";

/**
 * Epic 337 — the twelve lines the reader carries into the call where they answer
 * the offer on the table. Second person, never to the company; the counter-letter
 * drafts the email that leaves the reader, this writes the sheet they sit with first.
 * Ask-first: nothing is written on mount; the button carries the Hint.
 */
export function OfferNegotiationPrep({ rowId }: { rowId: string }) {
  const { t, locale } = useLocale();
  const prep = useNegotiationPrep();
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
      // clipboard is not the product's promise — the sheet stands on screen
    }
  };

  return (
    <div className="mt-3 rounded-lg border border-border/50 bg-muted/20 p-3">
      <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
        {t("offers.negotiationPrepTitle")}
      </p>
      {text ? (
        <>
          <p className="mt-1 whitespace-pre-wrap text-sm leading-relaxed text-foreground/90">{text}</p>
          <Button variant="ghost" size="sm" className="mt-2" onClick={() => void copy()} aria-label={t("common.copy")} title={t("common.copy")}>
            {copied ? <Check aria-hidden /> : <Copy aria-hidden />}
            {copied ? t("offers.negotiationPrepCopied") : t("offers.negotiationPrepCopy")}
          </Button>
        </>
      ) : silent ? (
        <p className="mt-1 text-xs text-muted-foreground">{t("offers.negotiationPrepSilent")}</p>
      ) : (
        <>
          <p className="mt-1 text-xs text-muted-foreground">{t("offers.negotiationPrepHint")}</p>
          <Hint label={t("offers.negotiationPrepHint")}>
            <Button
              variant="outline"
              size="sm"
              className="mt-2"
              loading={prep.isPending}
              onClick={() =>
                prep.mutate(
                  { id: rowId, locale },
                  {
                    onSuccess: (out) => {
                      if (out.prep) {
                        setText(out.prep);
                      } else {
                        setSilent(true);
                      }
                    },
                  },
                )
              }
            >
              <ClipboardList aria-hidden />
              {t("offers.negotiationPrepButton")}
            </Button>
          </Hint>
        </>
      )}
    </div>
  );
}
