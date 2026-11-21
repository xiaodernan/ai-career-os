"use client";

import * as React from "react";
import { ArrowRight, Sparkles } from "lucide-react";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useLocale } from "@/lib/i18n/locale-context";

/**
 * Skill summary card (Epic 349).
 * Shows top skills with proficiency — real values, no NaN.
 */
export function SkillSummaryCard({
  skills = [],
}: {
  skills?: ReadonlyArray<{ name: string; proficiency?: number }>;
}) {
  const { t } = useLocale();
  const topSkills = skills.slice(0, 4);

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-base">
          <Sparkles className="size-4 text-muted-foreground" aria-hidden />
          {t("dashboard.topSkills")}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {topSkills.length === 0 ? (
          <p className="text-sm text-muted-foreground">{t("dashboard.noSkillsYet")}</p>
        ) : (
          <ul className="space-y-2">
            {topSkills.map((skill) => {
              const prof = Math.max(0, Math.min(100, skill.proficiency ?? 0));
              const band =
                prof >= 80 ? "bg-success" : prof >= 60 ? "bg-primary" : prof >= 40 ? "bg-warning" : "bg-muted-foreground";
              return (
                <li key={skill.name} className="space-y-1">
                  <div className="flex items-center justify-between text-sm">
                    <span className="font-medium">{skill.name}</span>
                    <span className="tabular-nums text-muted-foreground">{Math.round(prof)}%</span>
                  </div>
                  <div className="h-1.5 overflow-hidden rounded-full bg-muted">
                    <div className={cn("h-full rounded-full", band)} style={{ width: `${prof}%` }} />
                  </div>
                </li>
              );
            })}
          </ul>
        )}
        <Button variant="ghost" size="sm" asChild className="-ml-2">
          <Link href="/studio">
            {t("dashboard.viewAllSkills")}
            <ArrowRight aria-hidden className="size-3.5" />
          </Link>
        </Button>
      </CardContent>
    </Card>
  );
}
