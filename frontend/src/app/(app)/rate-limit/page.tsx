"use client";

import * as React from "react";
import { Activity, Gauge, ShieldCheck } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/common/error-state";
import { useRateLimitStatus } from "@/lib/hooks/ratelimit";
import { useLocale } from "@/lib/i18n/locale-context";
import { formatNumber } from "@/lib/format";

/**
 * The rate-limit dashboard (16.2): the current rate-limit configuration and the
 * caller's current bucket usage. Read-only, user-scoped.
 */
export default function RateLimitPage() {
  const { t } = useLocale();
  const status = useRateLimitStatus();
  const data = status.data;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{t("rateLimit.title")}</h1>
          <p className="text-sm text-muted-foreground">{t("rateLimit.description")}</p>
        </div>
        <Button variant="outline" size="sm" onClick={() => void status.refetch()}>
          {t("common.refresh")}
        </Button>
      </div>

      {status.isPending && (
        <div className="space-y-4">
          <Skeleton className="h-32 rounded-xl" />
          <Skeleton className="h-48 rounded-xl" />
        </div>
      )}

      {status.isError && (
        <ErrorState
          title={t("rateLimit.loadFailed")}
          error={status.error}
          onRetry={() => void status.refetch()}
          retrying={status.isFetching}
        />
      )}

      {!status.isPending && !status.isError && data && (
        <>
          {/* Status */}
          <Card>
            <CardHeader>
              <CardTitle>{t("rateLimit.rateLimiting")}</CardTitle>
              <CardDescription>{t("rateLimit.enabledDescription")}</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-3">
                <Badge
                  variant={data.enabled ? "success" : "secondary"}
                  className="text-sm"
                >
                  {data.enabled ? t("rateLimit.enabled") : t("rateLimit.disabled")}
                </Badge>
                <span className="text-sm text-muted-foreground">
                  {data.enabled
                    ? t("rateLimit.throttledPerUser")
                    : "No throttling is applied."}
                </span>
              </div>
            </CardContent>
          </Card>

          {/* Limits */}
          <div className="grid gap-4 sm:grid-cols-2">
            <Card>
              <CardHeader>
                <CardDescription className="flex items-center gap-1.5">
                  <Gauge className="size-3.5" aria-hidden />
                  {t("rateLimit.aiEndpoints")}
                </CardDescription>
                <CardTitle className="text-2xl font-semibold tabular-nums">
                  {formatNumber(data.aiPerMinute ?? 0)}/min
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">{t("rateLimit.aiDescription")}</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardDescription className="flex items-center gap-1.5">
                  <ShieldCheck className="size-3.5" aria-hidden />
                  {t("rateLimit.authEndpoints")}
                </CardDescription>
                <CardTitle className="text-2xl font-semibold tabular-nums">
                  {formatNumber(data.authPerMinute ?? 0)}/min
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">{t("rateLimit.authDescription")}</p>
              </CardContent>
            </Card>
          </div>

          {/* Remaining */}
          <Card>
            <CardHeader>
              <CardTitle>{t("rateLimit.yourRemainingQuota")}</CardTitle>
              <CardDescription>{t("rateLimit.quotaDescription")}</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="rounded-lg border border-border/50 p-4">
                <p className="text-sm text-muted-foreground">AI endpoints</p>
                <p className="mt-1 text-2xl font-semibold tabular-nums">
                  {formatNumber(data.aiRemaining ?? 0)}
                  <span className="text-sm font-normal text-muted-foreground">
                    / {formatNumber(data.aiPerMinute ?? 0)}
                  </span>
                </p>
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
