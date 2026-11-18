"use client";

import * as React from "react";
import { Check, Copy, Sparkles } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Hint } from "@/components/ui/hint";
import { Badge } from "@/components/ui/badge";
import { useLocale } from "@/lib/i18n/locale-context";
import { useDecodeReply } from "@/lib/hooks/replies";
import type { InboundMail } from "@/lib/api/types";

/**
 * Epic 332 — the analyst's read of one letter.
 *
 * The reader taps once; the server answers with the letter's own facts: the intent the
 * words settle, the single date the letter states (or an absent one), the next action,
 * what they ask, and a ready-to-edit reply. No reading happens before the tap — a
 * letter nobody asked about is nobody's presumption — and an analyst with nothing
 * grounded to stand behind says nothing rather than something confident.
 */
export function InboundDecode({ mail }: { mail: InboundMail }) {
  const { t, locale } = useLocale();
  const decode = useDecodeReply();
  const [copied, setCopied] = React.useState(false);
  const result = decode.data?.decode ?? null;

  const copy = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error(t("replies.decodeError"));
    }
  };

  const deadline = result?.deadline
    ? new Date(`${result.deadline}T00:00:00Z`).toLocaleDateString(
        locale === "zh" ? "zh-CN" : "en-US",
        { year: "numeric", month: "long", day: "numeric", timeZone: "UTC" }
      )
    : null;

  return (
    <div className="mt-2 border-t border-border/60 pt-2">
      <div className="flex flex-wrap items-center gap-2">
        <Hint label={t("replies.decodeHint")}>
          <Button
            variant="ai"
            size="sm"
            loading={decode.isPending}
            onClick={() => decode.mutate({ id: mail.id, locale })}
          >
            <Sparkles aria-hidden />
            {result ? t("replies.decodeAgain") : t("replies.decodeAction")}
          </Button>
        </Hint>
        {decode.isPending ? (
          <span className="text-xs text-muted-foreground">{t("replies.decodePending")}</span>
        ) : null}
      </div>

      {decode.isError ? (
        <p role="alert" className="mt-2 text-xs text-destructive">
          {t("replies.decodeError")}
        </p>
      ) : null}

      {decode.data && !result ? (
        <p className="mt-2 text-xs text-muted-foreground">{t("replies.decodeEmpty")}</p>
      ) : null}

      {result ? (
        <div aria-live="polite" className="mt-2 space-y-2 rounded-lg border border-ai/30 bg-ai/5 p-3 text-sm">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="ai">{t(`replies.intents.${result.intent}`)}</Badge>
            {deadline ? (
              <span className="text-xs text-muted-foreground">
                {t("replies.decodeDeadline", { date: deadline })}
              </span>
            ) : null}
          </div>
          {result.next_action ? (
            <p className="text-sm leading-relaxed">
              <span className="mr-1 text-xs font-medium text-muted-foreground">
                {t("replies.decodeNextActionLabel")}
              </span>
              {result.next_action}
            </p>
          ) : null}
          {result.asks.length ? (
            <div>
              <p className="text-xs font-medium text-muted-foreground">
                {t("replies.decodeAsksLabel")}
              </p>
              <ul className="mt-1 list-disc space-y-0.5 pl-4 text-xs leading-relaxed">
                {result.asks.map((ask, i) => (
                  <li key={i}>{ask}</li>
                ))}
              </ul>
            </div>
          ) : null}
          {result.reply ? (
            <div>
              <div className="flex items-center justify-between gap-2">
                <p className="text-xs font-medium text-muted-foreground">
                  {t("replies.decodeReplyLabel")}
                </p>
                <Hint label={t("replies.decodeCopyHint")}>
                  <Button
                    variant="ghost"
                    size="sm"
                    aria-label={t("replies.decodeCopy")}
                    onClick={() => void copy(result.reply ?? "")}
                  >
                    {copied ? <Check aria-hidden /> : <Copy aria-hidden />}
                    {copied ? t("replies.decodeCopied") : t("replies.decodeCopy")}
                  </Button>
                </Hint>
              </div>
              <p className="mt-1 whitespace-pre-wrap rounded-md border border-border/60 bg-background p-2 text-xs leading-relaxed">
                {result.reply}
              </p>
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
