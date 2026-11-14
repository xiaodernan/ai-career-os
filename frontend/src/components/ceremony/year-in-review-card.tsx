"use client";

import * as React from "react";
import { Download, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useLocale } from "@/lib/i18n/locale-context";
import {
  REVIEW_CARD_HEIGHT,
  REVIEW_CARD_WIDTH,
  drawReviewCard,
  type ReviewCardNumbers,
} from "@/lib/review-card";

/**
 * The year in review (Epic 224) — the keepsake that travels.
 *
 * The ceremony is for the reader alone; this card makes one image out of the
 * same real numbers — applications, interviews, offers, letters kept, days
 * showed up, actions taken — and hands it over as a PNG. Nothing is drawn
 * that no route answered; the canvas is a re-rendering of the reader's own
 * record, sized for a post, drawn entirely on-device.
 */
export function YearInReviewCard({ numbers }: { numbers: ReviewCardNumbers }) {
  const { t, locale } = useLocale();
  const today = new Date().toLocaleDateString(locale === "zh" ? "zh-CN" : "en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });

  const strings = {
    eyebrow: t("ceremony.reviewEyebrow"),
    headline: t("ceremony.reviewHeadline"),
    applications: t("ceremony.statApplications"),
    interviews: t("ceremony.statInterviews"),
    offers: t("ceremony.statOffers"),
    letters: t("ceremony.statLetters"),
    daysShowed: t("ceremony.statDays"),
    stripRight: t("ceremony.reviewStripRight"),
    signOff: t("ceremony.reviewSignOff"),
    dateLine: today,
  };

  const download = () => {
    const canvas = document.createElement("canvas");
    canvas.width = REVIEW_CARD_WIDTH;
    canvas.height = REVIEW_CARD_HEIGHT;
    const ctx = canvas.getContext("2d");
    if (!ctx) {
      toast.error(t("ceremony.reviewFailed"));
      return;
    }
    drawReviewCard(ctx, numbers, strings);
    canvas.toBlob((blob) => {
      if (!blob) {
        toast.error(t("ceremony.reviewFailed"));
        return;
      }
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `career-os-review-${numbers.year}.png`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success(t("ceremony.reviewSaved"));
    }, "image/png");
  };

  return (
    <Card data-testid="year-in-review" className="print:hidden border-primary/20 bg-gradient-to-br from-violet-950 via-card to-card">
      <CardHeader className="flex flex-row items-start gap-4 space-y-0">
        <div className="flex size-10 shrink-0 items-center justify-center rounded-xl border border-primary/30 bg-primary/15 text-primary">
          <Sparkles aria-hidden className="size-5" />
        </div>
        <div className="min-w-0">
          <CardTitle className="text-base">{t("ceremony.reviewTitle")}</CardTitle>
          <CardDescription>{t("ceremony.reviewDescription")}</CardDescription>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div
          aria-hidden="true"
          className="grid grid-cols-2 gap-2 rounded-xl border border-white/10 bg-[#12101d] p-4"
        >
          <div className="flex flex-col gap-1 rounded-lg bg-[#1b1830] p-4">
            <span className="text-2xl font-semibold tabular-nums text-[#efeaf6]">{numbers.applications}</span>
            <span className="text-2xs uppercase tracking-wide text-[#8b86a3]">{strings.applications}</span>
          </div>
          <div className="flex flex-col gap-1 rounded-lg bg-[#1b1830] p-4">
            <span className="text-2xl font-semibold tabular-nums text-[#efeaf6]">{numbers.interviews}</span>
            <span className="text-2xs uppercase tracking-wide text-[#8b86a3]">{strings.interviews}</span>
          </div>
          <div className="flex flex-col gap-1 rounded-lg bg-[#1b1830] p-4">
            <span className="text-2xl font-semibold tabular-nums text-[#efeaf6]">{numbers.offers}</span>
            <span className="text-2xs uppercase tracking-wide text-[#8b86a3]">{strings.offers}</span>
          </div>
          <div className="flex flex-col gap-1 rounded-lg bg-[#1b1830] p-4">
            <span className="text-2xl font-semibold tabular-nums text-[#efeaf6]">{numbers.grandTotal}</span>
            <span className="text-2xs uppercase tracking-wide text-[#8b86a3]">{strings.stripRight}</span>
          </div>
        </div>
        <p className="sr-only">{t("ceremony.reviewAriaHint", { total: numbers.grandTotal, days: numbers.daysShowed })}</p>
        <Button variant="ai" size="sm" onClick={download}>
          <Download aria-hidden className="size-4" />
          {t("ceremony.reviewDownload")}
        </Button>
      </CardContent>
    </Card>
  );
}
