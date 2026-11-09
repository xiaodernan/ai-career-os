"use client";

import { Network } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useServiceTopology } from "@/lib/hooks/monitoring";
import { useLocale } from "@/lib/i18n/locale-context";

/**
 * The fleet the backend can see (roadmap 100).
 *
 * <p>It reads the deployment's discovery answer rather than a configured inventory, so
 * the page cannot disagree with the load balancer: a service that appears here is one
 * the backend would route to, and one that disappears was evicted from the registry.
 * The card sits outside the agent-health conditional for the same reason the nightly
 * history does -- a failed report about agents says nothing about the deployment.
 */
export function ServiceTopology() {
  const { t } = useLocale();
  const topology = useServiceTopology();
  const data = topology.data;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Network className="size-4" aria-hidden />
          {t("monitoring.topologyTitle")}
        </CardTitle>
        <CardDescription>{t("monitoring.topologyDescription")}</CardDescription>
      </CardHeader>
      <CardContent>
        {topology.isPending && <Skeleton className="h-24 rounded-lg" />}

        {topology.isError && (
          <p className="text-sm text-muted-foreground">{t("monitoring.topologyUnavailable")}</p>
        )}

        {data && data.services.length === 0 && (
          <p className="text-sm text-muted-foreground">{t("monitoring.topologyEmpty")}</p>
        )}

        {data && data.services.length > 0 && (
          <>
            <div className="mb-3 flex items-center gap-2 text-xs text-muted-foreground">
              {t("monitoring.topologyRegistry")}
              <Badge variant={data.registry === "eureka" ? "success" : "secondary"}>
                {data.registry === "eureka"
                  ? t("monitoring.topologyRegistryEureka")
                  : t("monitoring.topologyRegistryConfiguration")}
              </Badge>
            </div>
            <ul className="space-y-2">
              {data.services.map((service) => (
                <li key={service.name} className="rounded-lg border border-border/50 p-3">
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-sm font-medium">{service.name}</p>
                    <Badge variant="secondary">
                      {t("monitoring.topologyInstances", { count: service.instances.length })}
                    </Badge>
                  </div>
                  <ul className="mt-2 space-y-1">
                    {service.instances.map((instance) => (
                      <li
                        key={instance.instanceId}
                        className="truncate font-mono text-xs text-muted-foreground"
                      >
                        {instance.uri}
                      </li>
                    ))}
                  </ul>
                </li>
              ))}
            </ul>
          </>
        )}
      </CardContent>
    </Card>
  );
}
