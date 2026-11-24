"use client";

import * as React from "react";
import Link from "next/link";
import { Library } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Hint } from "@/components/ui/hint";
import { useLocale } from "@/lib/i18n/locale-context";
import { legacyOf } from "@/lib/legacy";
import type { LegacyInput } from "@/lib/legacy";

/**
 * What this search leaves behind for the next one (Epic 371).
 *
 * Brief VI asks for "新的后续环节" — and the honest one is that a search ends and
 * another begins. The ceremony says what the loop WAS; this card reads the same
 * ledger and says what it LEFT: the material worth reusing, the stage that cost the
 * most, and the one lesson the numbers support.
 *
 * It renders nothing at all when the ledger is thin. A reader who did one thing
 * should not be handed a retrospective, and a card that invents a lesson is worse
 * than no card.
 */
export function LegacyCard({ input }: { input: LegacyInput }) {
  const { t } = useLocale();
  const legacy = React.useMemo(() => legacyOf(input), [input]);

  const saysNothing =
    legacy.reuse.length === 0 && legacy.costliestStage === null && legacy.lesson === null;
  if (saysNothing) return null;

  return (
    <Card data-testid="legacy-card" className="border-primary/15 shadow-card">
      <CardHeader className="pb-3">
        <div className="flex items-center gap-2">
          <span className="flex size-8 shrink-0 items-center justify-center rounded-lg border border-primary/25 bg-primary/10 text-primary">
            <Library aria-hidden className="size-4" />
          </span>
          <div className="min-w-0">
            <CardTitle className="text-base">{t("legacy.title")}</CardTitle>
            <p className="text-xs text-muted-foreground">{t("legacy.description")}</p>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {legacy.lesson ? (
          <div className="rounded-xl border border-primary/20 bg-primary/[0.05] p-4">
            <p className="text-2xs font-semibold uppercase tracking-widest text-primary">
              {t("legacy.lessonEyebrow")}
            </p>
            <p className="mt-1 text-sm font-medium">{t(legacy.lesson.titleKey)}</p>
            <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
              {t(legacy.lesson.bodyKey)}
            </p>
          </div>
        ) : null}

        {legacy.costliestStage ? (
          <p className="text-xs leading-relaxed text-muted-foreground">
            {t("legacy.costliestStage", {
              stage: t(`stages.${legacy.costliestStage.id}`),
              count: legacy.costliestStage.count,
            })}
          </p>
        ) : null}

        {legacy.reuse.length > 0 ? (
          <ul className="grid gap-2 sm:grid-cols-2">
            {legacy.reuse.map((row) => (
              <li
                key={row.id}
                className="flex items-center justify-between gap-3 rounded-xl border border-border/60 bg-card/60 p-3"
              >
                <div className="min-w-0">
                  <p className="text-sm font-medium">{t(row.titleKey, { count: row.count })}</p>
                  <p className="mt-0.5 text-xs leading-relaxed text-muted-foreground">
                    {t(row.bodyKey, { count: row.count })}
                  </p>
                </div>
                <Hint anchor="span" label={t("ceremony.hintLegacyOpen")}>
                  <Button asChild size="sm" variant="outline" className="shrink-0">
                    <Link href={row.href}>{t("legacy.open")}</Link>
                  </Button>
                </Hint>
              </li>
            ))}
          </ul>
        ) : null}
      </CardContent>
    </Card>
  );
}
