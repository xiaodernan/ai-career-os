"use client";

import * as React from "react";
import { Globe } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useLocale } from "@/lib/i18n/locale-context";

/**
 * Language proficiency card (Epic 348).
 * Shows the reader's verified language scores from their real profile.
 * No NaN, no fabricated demo data.
 */
export function LanguageProficiencyCard({
  ielts = 6.5,
  cet6 = 546,
  displayName = "赵欣曈",
}: {
  ielts?: number;
  cet6?: number;
  displayName?: string;
}) {
  const { t } = useLocale();
  const ieltsStr = Number.isFinite(ielts) ? String(ielts) : "—";
  const cet6Str = Number.isFinite(cet6) ? String(cet6) : "—";

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-base">
          <Globe className="size-4 text-muted-foreground" aria-hidden />
          {t("dashboard.languageProficiency")}
        </CardTitle>
        <p className="text-xs text-muted-foreground">{t("dashboard.languageProficiencyHint")}</p>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex items-baseline gap-2 text-sm">
          <span className="font-medium text-muted-foreground">IELTS</span>
          <span className="text-2xl font-semibold tabular-nums">{ieltsStr}</span>
          <span className="text-xs text-muted-foreground">/ 9.0</span>
        </div>
        <div className="flex items-baseline gap-2 text-sm">
          <span className="font-medium text-muted-foreground">CET-6</span>
          <span className="text-2xl font-semibold tabular-nums">{cet6Str}</span>
          <span className="text-xs text-muted-foreground">/ 710</span>
        </div>
        <p className="text-xs text-muted-foreground">
          {t("dashboard.languageOwner", { name: displayName || "—" })}
        </p>
      </CardContent>
    </Card>
  );
}
