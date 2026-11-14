"use client";

import * as React from "react";
import { Check, Copy, Download, Feather, Send, X } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { copyText } from "@/lib/format";
import { useLocale } from "@/lib/i18n/locale-context";
import { useOfferShelf } from "@/lib/hooks/resources";

/**
 * The bookend (Epic 211) — the two letters every negotiation ends with, drafted
 * from the row the reader already holds.
 *
 * The shelf knows the label, the decision and the numbers. The day-one packet
 * covers the chores after the yes. This card closes the loop the other two doors
 * never open: the letter that accepts the offer and the letter that leaves the
 * other offers warmly. No model call, no network — the words ride the i18n table,
 * interpolate the company/role the reader typed, and never claim a fact beyond it.
 *
 * The yes names the company, the role and the start; the no names the company,
 * the role, declines with grace, and leaves the door open a crack. Both travel
 * in a mailto with the body filled in, or a plain text download, or one copy to
 * the reader's clipboard. Silence is the one message this product will never
 * write for the reader.
 *
 * The row label "Acme — Senior Backend" splits on the last " — " into the company
 * (first chunk) and the role (second); a bare word travels whole as the company
 * and the role becomes "the role" in both letters.
 */

const splitLabel = (label: string): { company: string; role: string } => {
  const trimmed = label.trim();
  for (const sep of [" — ", " – ", " - "]) {
    const idx = trimmed.lastIndexOf(sep);
    if (idx !== -1) {
      const company = trimmed.slice(0, idx).trim();
      const role = trimmed.slice(idx + sep.length).trim();
      if (company) return { company, role };
    }
  }
  return { company: trimmed || "—", role: "" };
};

/** Exported for the tests: the label split is the only piece of this logic worth pinning. */
export const splitLabelForTest = splitLabel;

export function OfferReplies() {
  const { t } = useLocale();
  const shelf = useOfferShelf();
  const items = shelf.data?.items ?? [];
  const accepted = items.find((row) => row.decision === "accepted") ?? null;
  const declined = items.filter((row) => row.decision === "declined");

  if (!accepted && declined.length === 0) return null;

  return (
    <Card
      data-testid="offer-replies"
      className="overflow-hidden border-primary/20 bg-gradient-to-br from-primary/5 via-card to-card shadow-card"
    >
      <CardHeader className="flex flex-row items-start gap-4 space-y-0">
        <div className="flex size-10 shrink-0 items-center justify-center rounded-xl border border-primary/25 bg-primary/10 text-primary">
          <Feather aria-hidden className="size-5" />
        </div>
        <div className="min-w-0">
          <CardTitle className="text-base">{t("offers.repliesTitle")}</CardTitle>
          <CardDescription>{t("offers.repliesDescription")}</CardDescription>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {accepted ? (
          <ReplyRow
            id="yes"
            testId="reply-yes"
            kind={t("offers.replyYesKind")}
            label={accepted.label}
            line={t("offers.replyYesLine", { company: splitLabel(accepted.label).company })}
            caption={t("offers.replyYesCaption")}
            letter={t("offers.replyYesBody", {
              company: splitLabel(accepted.label).company,
              role: splitLabel(accepted.label).role || t("offers.roleFallback"),
            })}
          />
        ) : null}
        {declined.map((row) => (
          <ReplyRow
            key={row.id}
            id={`no-${row.id}`}
            testId="reply-no"
            kind={t("offers.replyNoKind")}
            label={row.label}
            line={t("offers.replyNoLine", { company: splitLabel(row.label).company })}
            caption={t("offers.replyNoCaption")}
            letter={t("offers.replyNoBody", {
              company: splitLabel(row.label).company,
              role: splitLabel(row.label).role || t("offers.roleFallback"),
            })}
          />
        ))}
      </CardContent>
    </Card>
  );
}

function ReplyRow({
  kind,
  label,
  line,
  caption,
  letter,
  id,
  testId,
}: {
  kind: string;
  label: string;
  line: string;
  caption: string;
  letter: string;
  id: string;
  testId: string;
}) {
  const { t } = useLocale();
  const [reveal, setReveal] = React.useState(false);
  const [copied, setCopied] = React.useState(false);

  const copy = async () => {
    const ok = await copyText(letter);
    setCopied(ok);
    window.setTimeout(() => setCopied(false), 1800);
  };
  const download = () => {
    const blob = new Blob([letter], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "letter.txt";
    anchor.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div data-testid={testId} className="rounded-xl border border-border/70 bg-card/60 p-4 backdrop-blur-sm transition-shadow duration-200 hover:shadow-soft">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="text-2xs font-normal text-muted-foreground">
              {kind}
            </Badge>
            <p className="truncate text-sm font-medium" title={label}>{label}</p>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">{line}</p>
        </div>
        <div className="flex shrink-0 items-center gap-1.5">
          <Button variant="ghost" size="sm" onClick={() => setReveal((v) => !v)} aria-expanded={reveal}>
            {reveal
              ? <X aria-hidden className="size-4" />
              : <Feather aria-hidden className="size-4" />}
            <span className="hidden sm:inline">{reveal ? t("offers.replyHide") : t("offers.replyRead")}</span>
          </Button>
        </div>
      </div>

      {reveal ? (
        <div className="mt-3 space-y-3 border-t border-border/60 pt-3">
          <pre className="whitespace-pre-wrap rounded-lg border border-border/60 bg-background/60 p-4 text-xs leading-relaxed text-foreground/90">
            {letter}
          </pre>
          <div className="flex flex-wrap items-center gap-1.5">
            <Button variant="outline" size="sm" onClick={copy} data-testid={`${testId}-copy`}>
              {copied
                ? <Check aria-hidden className="size-4 text-success" />
                : <Copy aria-hidden className="size-4" />}
              <span>{copied ? t("common.copied") : t("common.copy")}</span>
            </Button>
            <Button variant="ghost" size="sm" onClick={download} data-testid={`${testId}-download`}>
              <Download aria-hidden className="size-4" />
              <span>{t("offers.replyDownload")}</span>
            </Button>
            <Button asChild variant="ai" size="sm">
              <a href={`mailto:?subject=${encodeURIComponent("Thank you — " + label)}&body=${encodeURIComponent(letter)}`}>
                <Send aria-hidden className="size-4" />
                <span>{t("offers.replyMailto")}</span>
              </a>
            </Button>
          </div>
          <p className="text-2xs text-muted-foreground">{caption}</p>
        </div>
      ) : null}
    </div>
  );
}
