"use client";

import * as React from "react";
import { ArrowRight, Map } from "lucide-react";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { TOUR_HREFS, readTourVisits, tourProgress } from "@/lib/tour";
import { useLocale } from "@/lib/i18n/locale-context";

/**
 * Nine quests progress card (Epic 350).
 * Reflects the same tour state as the dashboard's nine-quests card, in a compact form.
 */
export function NineQuestsProgressCard() {
  const { t } = useLocale();
  const [visited, setVisited] = React.useState(0);

  React.useEffect(() => {
    setVisited(tourProgress(readTourVisits()).done);
  }, []);

  const total = TOUR_HREFS.length;
  const pct = total > 0 ? Math.round((visited / total) * 100) : 0;

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-base">
          <Map className="size-4 text-muted-foreground" aria-hidden />
          {t("dashboard.questsProgressTitle")}
        </CardTitle>
        <p className="text-xs text-muted-foreground">{t("dashboard.questsProgressHint")}</p>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-sm text-muted-foreground">
          {t("dashboard.questsProgress", {
            completed: String(visited),
            total: String(total),
            progress: String(pct),
          })}
        </p>
        <div className="h-2 overflow-hidden rounded-full bg-muted" aria-hidden>
          <div
            className={cn("h-full rounded-full bg-primary transition-all duration-500")}
            style={{ width: `${pct}%` }}
          />
        </div>
        <Button variant="ghost" size="sm" asChild className="-ml-2">
          <Link href="/tour">
            {visited >= total ? t("dashboard.revisitTour") : t("dashboard.startQuests")}
            <ArrowRight aria-hidden className="size-3.5" />
          </Link>
        </Button>
      </CardContent>
    </Card>
  );
}
