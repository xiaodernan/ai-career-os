"use client";

import * as React from "react";
import { Compass } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { useLocale } from "@/lib/i18n/locale-context";
import { formatDate } from "@/lib/format";
import { searchPortrait, type ShapeInput } from "@/lib/search-shape";

/**
 * The shape of one reader's search (Epic 376).
 *
 * Brief VI asks for "宏观史诗叙事 + 细节包罗万象", and the honest version of that on a job
 * search is a portrait: not "you applied to 12 jobs" but "your search was a burst that
 * lasted three weeks and then stopped". Two readers with the same count can have
 * completely different searches, and the count cannot tell them apart.
 *
 * It is a description, never a score: a burst is not better or worse than a slow burn,
 * and the card says so. A reader with one application gets a fact rather than a pattern.
 */
const SHAPE_TITLE: Record<string, string> = {
  single: "applications.portraitSingleTitle",
  burst: "applications.portraitBurstTitle",
  steady: "applications.portraitSteadyTitle",
  "long-tail": "applications.portraitLongTailTitle",
  resting: "applications.portraitRestingTitle",
};

const SHAPE_BODY: Record<string, string> = {
  single: "applications.portraitSingleBody",
  burst: "applications.portraitBurstBody",
  steady: "applications.portraitSteadyBody",
  "long-tail": "applications.portraitLongTailBody",
  resting: "applications.portraitRestingBody",
};

export function SearchPortraitCard({ input }: { input: ShapeInput }) {
  const { t, locale } = useLocale();
  const portrait = React.useMemo(() => searchPortrait(input), [input]);

  // An empty board has no shape, and inventing one would be the exact failure this
  // product exists to avoid.
  if (portrait.count === 0) return null;

  const vars = {
    count: portrait.count,
    span: portrait.spanDays ?? 0,
    busiest: portrait.busiest?.count ?? 0,
    from: portrait.busiest ? formatDate(portrait.busiest.start, locale) : "",
  };

  return (
    <Card data-testid="portrait-card" className="border-primary/15 shadow-card">
      <CardContent className="flex flex-wrap items-center gap-4 p-5">
        <span className="flex size-10 shrink-0 items-center justify-center rounded-xl border border-primary/25 bg-primary/10 text-primary">
          <Compass aria-hidden className="size-5" />
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-2xs font-semibold uppercase tracking-widest text-primary">
            {t("applications.portraitEyebrow")}
          </p>
          <p className="mt-1 text-sm font-medium">{t(SHAPE_TITLE[portrait.shape], vars)}</p>
          <p className="mt-0.5 text-xs leading-relaxed text-muted-foreground">
            {t(SHAPE_BODY[portrait.shape], vars)}
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
