"use client";

import * as React from "react";
import { toast } from "sonner";
import { FileSearch, Layers, Radar, Scissors } from "lucide-react";
import { PageHeader } from "@/components/common/page-header";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { useDedupeJobs, useFreshnessSweep, useIngestPlan, useParseFeed } from "@/lib/hooks/ingestion";
import { useLocale } from "@/lib/i18n/locale-context";
import { ScheduledFeedsPanel } from "@/components/ingestion/scheduled-feeds-panel";
import type { RawPosting } from "@/lib/api/types";

/**
 * The job ingestion page (14.2-14.3): parse a feed, deduplicate it against the
 * corpus, sweep it for freshness, and build one create/update/close plan.
 *
 * The whole surface is deterministic — no model runs here, and every count the
 * page shows is the engine's own.
 */
export default function IngestionPage() {
  const { t } = useLocale();
  const parseFeed = useParseFeed();
  const dedupe = useDedupeJobs();
  const sweep = useFreshnessSweep();
  const plan = useIngestPlan();

  const [feed, setFeed] = React.useState("");
  const [postings, setPostings] = React.useState<RawPosting[]>([]);

  const runParse = React.useCallback(() => {
    if (!feed.trim()) return;
    parseFeed.mutate(
      // The engine detects the shape from the text; the source is the
      // label the postings carry, so it has to name the shape they came
      // from rather than a fixed one.
      { feed, source: feed.trim().startsWith("<") ? "rss" : "board" },
      {
        onSuccess: (out) => {
          const rows = out.postings ?? [];
          setPostings(rows);
          toast.success(t("ingestion.parsedToast", { count: out.count ?? rows.length }));
        },
      }
    );
  }, [feed, parseFeed, t]);

  const runDedupe = React.useCallback(() => {
    if (!postings.length) return;
    dedupe.mutate(postings, {
      onSuccess: (out) => {
        toast.success(
          t("ingestion.dedupedToast", {
            unique: out.uniqueCount ?? 0,
            duplicate: out.duplicateCount ?? 0,
          })
        );
      },
    });
  }, [postings, dedupe, t]);

  const runSweep = React.useCallback(() => {
    if (!postings.length) return;
    sweep.mutate({ postings }, {
      onSuccess: (out) => {
        const c = out.counts;
        toast.success(
          c
            ? t("ingestion.sweepSummary", {
                fresh: c.fresh,
                stale: c.stale,
                expired: c.expired,
                undated: c.undated,
              })
            : t("ingestion.sweepDone")
        );
      },
    });
  }, [postings, sweep, t]);

  const runPlan = React.useCallback(() => {
    if (!feed.trim()) return;
    plan.mutate({ feed, source: feed.trim().startsWith("<") ? "rss" : "board" }, {
      onSuccess: (out) => {
        const c = out.counts;
        toast.success(
          c
            ? t("ingestion.planSummary", {
                create: c.create,
                update: c.update,
                close: c.close,
              })
            : t("ingestion.planReady")
        );
      },
    });
  }, [feed, plan, t]);

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <PageHeader
        title={t("ingestion.title")}
        description={t("ingestion.sweepDescription")}
      />

      <ScheduledFeedsPanel />

      {/* Feed */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">{t("ingestion.sourceFeed")}</CardTitle>
          <CardDescription>{t("ingestion.sourceDescription")}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="feed">{t("ingestion.feedContent")}</Label>
            <Textarea
              id="feed"
              value={feed}
              onChange={(e) => setFeed(e.target.value)}
              placeholder={"<rss>…</rss>  or  { \"jobs\": [ … ] }"}
              rows={8}
              className="font-mono text-xs"
            />
          </div>
          <div className="flex flex-wrap gap-2">
            <Button
              variant="ai"
              size="sm"
              loading={parseFeed.isPending}
              disabled={!feed.trim()}
              onClick={runParse}
            >
              <FileSearch aria-hidden />
              {t("ingestion.parse")}
            </Button>
            <Button
              variant="outline"
              size="sm"
              loading={plan.isPending}
              disabled={!feed.trim()}
              onClick={runPlan}
            >
              <Layers aria-hidden />
              {t("ingestion.buildThePlan")}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Postings */}
      {postings.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">{t("ingestion.parsedPostings")}</CardTitle>
            <CardDescription>
              {postings.length} {t("ingestion.parsedDescription")}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <ul className="max-h-64 space-y-2 overflow-y-auto">
              {postings.slice(0, 50).map((p, i) => (
                <li key={p.id ?? `${p.title}-${i}`} className="flex items-start gap-2 text-sm">
                  <span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-primary" aria-hidden />
                  <span className="min-w-0">
                    <span className="font-medium">{p.title || t("ingestion.untitledRole")}</span>
                    {p.company && (
                      <span className="text-muted-foreground"> · {p.company}</span>
                    )}
                    {p.location && (
                      <span className="text-muted-foreground"> · {p.location}</span>
                    )}
                  </span>
                </li>
              ))}
            </ul>
            <Separator />
            <div className="flex flex-wrap gap-2">
              <Button
                variant="outline"
                size="sm"
                loading={dedupe.isPending}
                onClick={runDedupe}
              >
                <Scissors aria-hidden />
                {t("ingestion.deduplicate")}
              </Button>
              <Button
                variant="outline"
                size="sm"
                loading={sweep.isPending}
                onClick={runSweep}
              >
                <Radar aria-hidden />
                {t("ingestion.freshnessSweep")}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Results */}
      {dedupe.data && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">{t("ingestion.deduplication")}</CardTitle>
            <CardDescription>{t("ingestion.dedupeDescription")}</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              <Badge variant="success">
                {t("ingestion.uniqueBadge", { count: dedupe.data.uniqueCount ?? 0 })}
              </Badge>
              <Badge variant="warning">
                {t("ingestion.duplicateBadge", { count: dedupe.data.duplicateCount ?? 0 })}
              </Badge>
              <Badge variant="outline">
                {t("ingestion.inputBadge", { count: dedupe.data.inputCount ?? 0 })}
              </Badge>
            </div>
          </CardContent>
        </Card>
      )}

      {sweep.data?.counts && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">{t("ingestion.freshness")}</CardTitle>
            <CardDescription>{t("ingestion.freshnessDescription")}</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              <Badge variant="success">
                {t("ingestion.freshBadge", { count: sweep.data.counts.fresh })}
              </Badge>
              <Badge variant="warning">
                {t("ingestion.staleBadge", { count: sweep.data.counts.stale })}
              </Badge>
              <Badge variant="destructive">
                {t("ingestion.expiredBadge", { count: sweep.data.counts.expired })}
              </Badge>
              <Badge variant="outline">
                {t("ingestion.undatedBadge", { count: sweep.data.counts.undated })}
              </Badge>
            </div>
          </CardContent>
        </Card>
      )}

      {plan.data?.counts && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">{t("ingestion.ingestionPlan")}</CardTitle>
            <CardDescription>{t("ingestion.planDescription")}</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              <Badge variant="success">
                {plan.data.counts.create} {t("ingestion.toCreate")}
              </Badge>
              <Badge variant="warning">
                {plan.data.counts.update} {t("ingestion.toUpdate")}
              </Badge>
              <Badge variant="destructive">
                {plan.data.counts.close} {t("ingestion.toClose")}
              </Badge>
              <Badge variant="outline">
                {plan.data.counts.duplicates} {t("ingestion.duplicates")}
              </Badge>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
