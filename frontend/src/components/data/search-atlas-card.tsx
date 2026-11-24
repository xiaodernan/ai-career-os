"use client";

import * as React from "react";
import { Compass } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Hint } from "@/components/ui/hint";
import { Badge } from "@/components/ui/badge";
import { useSearchAtlas } from "@/lib/hooks/timeline";
import { useLocale } from "@/lib/i18n/locale-context";
import type { ExportBundle, SearchAtlas } from "@/lib/api/types";

/**
 * Epic 438 — the map of the search, drawn from the export the reader already has
 * in hand. Every count comes from a real row in that bundle; the engine draws a
 * region even when it is empty, so the quiet parts of the world are visible
 * rather than silently missing. Nothing is inferred and nothing is fetched.
 */
const rows = (value: unknown): unknown[] => (Array.isArray(value) ? value : []);

export function SearchAtlasCard({ bundle }: { bundle: ExportBundle }) {
  const { t } = useLocale();
  const atlas = useSearchAtlas();
  const [map, setMap] = React.useState<SearchAtlas | null>(null);

  const draw = () => {
    const data = (bundle.data ?? {}) as Record<string, unknown>;
    atlas.mutate(
      {
        applications: rows(data.applications),
        jobs: rows(data.saved_jobs),
        interviews: rows(data.interviews),
        letters: rows(data.cover_letters),
        notes: rows(data.notes),
        contacts: rows(data.contacts),
        offers: rows(data.offers),
      },
      { onSuccess: setMap },
    );
  };

  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between gap-3">
        <div>
          <CardTitle className="text-base">{t("data.atlasTitle")}</CardTitle>
          <CardDescription>{t("data.atlasDescription")}</CardDescription>
        </div>
        <Hint label={t("data.atlasHint")}>
          <Button variant="outline" size="sm" loading={atlas.isPending} onClick={draw}>
            <Compass aria-hidden />
            {atlas.isPending ? t("data.atlasDrawing") : t("data.atlasDraw")}
          </Button>
        </Hint>
      </CardHeader>
      <CardContent>
        {map?.regions && map.regions.length > 0 ? (
          <div className="space-y-3">
            <p className="text-xs text-muted-foreground">
              {t("data.atlasTotal", { count: map.total_evidence ?? 0 })}
            </p>
            <ul className="grid gap-2 sm:grid-cols-2">
              {map.regions.map((region) => (
                <li key={region.id} className="rounded-lg border border-border/70 p-3">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-sm font-medium">{region.title}</span>
                    <Badge variant={region.explored ? "success" : "outline"}>
                      {region.explored ? region.count : t("data.atlasUnexplored")}
                    </Badge>
                  </div>
                  <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{region.note}</p>
                </li>
              ))}
            </ul>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">{t("data.atlasDescription")}</p>
        )}
      </CardContent>
    </Card>
  );
}
