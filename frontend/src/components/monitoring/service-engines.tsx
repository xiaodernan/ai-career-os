"use client";

import { Cpu } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useDeploymentHealth } from "@/lib/hooks/monitoring";
import { useLocale } from "@/lib/i18n/locale-context";

/**
 * The engine fleet the backend can call right now (Epic 108.23).
 *
 * The `/health` probe reports one row per configured ai-service replica — the same
 * answer service routing decisions see. A second engine node shows up here without any
 * new route, and the fleet view lets an operator check whether a multi-replica setup is
 * actually live before blaming a model for a silent half fleet.
 */
export function ServiceEngines() {
  const { t } = useLocale();
  const health = useDeploymentHealth();
  const data = health.data;
  const nodes = data?.aiNodes ?? [];
  const ready = nodes.filter((node) => node.up).length;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Cpu className="size-4" aria-hidden />
          {t("monitoring.enginesTitle")}
        </CardTitle>
        <CardDescription>{t("monitoring.enginesDescription")}</CardDescription>
      </CardHeader>
      <CardContent>
        {health.isPending && <Skeleton className="h-20 rounded-lg" />}

        {health.isError && (
          <p className="text-sm text-muted-foreground">{t("monitoring.enginesUnavailable")}</p>
        )}

        {data && nodes.length > 0 && (
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">
              {t("monitoring.enginesReady", { count: ready, total: nodes.length })}
            </p>
            <ul className="space-y-2">
              {nodes.map((node) => (
                <li
                  key={node.url}
                  className="flex items-center justify-between gap-3 rounded-lg border border-border/50 p-3"
                >
                  <p className="truncate font-mono text-xs text-muted-foreground">{node.url}</p>
                  <Badge variant={node.up ? "success" : "destructive"}>
                    {node.up ? "UP" : "DOWN"}
                  </Badge>
                </li>
              ))}
            </ul>
          </div>
        )}

        {data && nodes.length === 0 && (
          <p className="text-sm text-muted-foreground">{t("monitoring.enginesEmpty")}</p>
        )}
      </CardContent>
    </Card>
  );
}