"use client";

import { ShieldCheck } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useServiceResilience } from "@/lib/hooks/monitoring";
import { useLocale } from "@/lib/i18n/locale-context";
import type { CircuitBreakerStatus } from "@/lib/api/types";

function stateVariant(state: string): "success" | "warning" | "destructive" | "secondary" {
  if (state === "CLOSED" || state === "DISABLED" || state === "METRICS_ONLY") return "success";
  if (state === "HALF_OPEN") return "warning";
  if (state === "OPEN" || state === "FORCED_OPEN") return "destructive";
  return "secondary";
}

/**
 * Spring Cloud Resilience4j circuit breaker states for the ai-service bridge (Epic 105).
 * Read-only operator view; complements topology by showing whether bridge doors are open.
 */
export function ServiceResilience() {
  const { t } = useLocale();
  const resilience = useServiceResilience();
  const data = resilience.data;
  const breakers: CircuitBreakerStatus[] = data?.circuitBreakers ?? [];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <ShieldCheck className="size-4" aria-hidden />
          {t("monitoring.resilienceTitle")}
        </CardTitle>
        <CardDescription>{t("monitoring.resilienceDescription")}</CardDescription>
      </CardHeader>
      <CardContent>
        {resilience.isPending && <Skeleton className="h-24 rounded-lg" />}

        {resilience.isError && (
          <p className="text-sm text-muted-foreground">{t("monitoring.resilienceUnavailable")}</p>
        )}

        {data && breakers.length === 0 && (
          <p className="text-sm text-muted-foreground">{t("monitoring.resilienceEmpty")}</p>
        )}

        {data && breakers.length > 0 && (
          <ul className="space-y-2">
            {breakers.map((breaker) => (
              <li key={breaker.name} className="rounded-lg border border-border/50 p-3">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-medium font-mono">{breaker.name}</p>
                  <Badge variant={stateVariant(breaker.state)}>{breaker.state}</Badge>
                </div>
                <p className="mt-1 text-xs text-muted-foreground">
                  {t("monitoring.resilienceCalls", {
                    failed: breaker.numberOfFailedCalls ?? 0,
                    ok: breaker.numberOfSuccessfulCalls ?? 0,
                    rejected: breaker.numberOfNotPermittedCalls ?? 0,
                  })}
                </p>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}