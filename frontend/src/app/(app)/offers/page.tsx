"use client";

import * as React from "react";
import { toast } from "sonner";
import { BadgeDollarSign, Handshake, Scale, Target } from "lucide-react";
import { PageHeader } from "@/components/common/page-header";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Textarea } from "@/components/ui/textarea";
import { EmptyState } from "@/components/common/empty-state";
import {
  useCompareOffers,
  useCounterOffer,
  useNegotiate,
  useSalaryBenchmark,
} from "@/lib/hooks/offers";
import { useLocale } from "@/lib/i18n/locale-context";
import { BarChart } from "@/components/common/bar-chart";
import { formatSalary } from "@/lib/format";

/**
 * The offers page (Epics 12.1-12.5): what the market pays, what to say back,
 * and which offer leads.
 *
 * Every number here is a deterministic read of the seeded corpus against the
 * candidate's own offer — the page never states a market fact the engine did not.
 */
export default function OffersPage() {
  const { t } = useLocale();
  const benchmark = useSalaryBenchmark();
  const negotiate = useNegotiate();
  const compare = useCompareOffers();
  const counter = useCounterOffer();

  const [role, setRole] = React.useState("");
  const [location, setLocation] = React.useState("");
  const [offerBase, setOfferBase] = React.useState("");
  const [matchScore, setMatchScore] = React.useState("");
  const [offerLabels, setOfferLabels] = React.useState("Offer A\nOffer B");

  const currency = "CNY";
  const roleOk = role.trim().length >= 2;
  const baseNum = Number(offerBase);
  const baseOk = Number.isFinite(baseNum) && baseNum > 0;
  const matchNum = matchScore.trim() === "" ? undefined : Number(matchScore) / 100;

  const runBenchmark = React.useCallback(() => {
    if (!roleOk) return;
    benchmark.mutate(
      { role: role.trim(), location: location.trim() || undefined, currency },
      { onSuccess: (out) => {
        if ((out.sampleSize ?? 0) === 0) {
          toast.error(t("offers.noBenchmark"));
        }
      } }
    );
  }, [role, location, roleOk, benchmark]);

  const runNegotiate = React.useCallback(() => {
    if (!roleOk || !baseOk) return;
    negotiate.mutate(
      {
        role: role.trim(),
        location: location.trim() || undefined,
        currency,
        offerBase: baseNum,
        matchScore: matchNum,
      },
      { onSuccess: () => toast.success("Negotiation plan ready.") }
    );
  }, [role, location, roleOk, baseOk, baseNum, matchNum, negotiate]);

  const runCounter = React.useCallback(() => {
    if (!roleOk || !baseOk) return;
    counter.mutate(
      {
        role: role.trim(),
        location: location.trim() || undefined,
        currency,
        offerBase: baseNum,
        matchScore: matchNum,
      },
      { onSuccess: () => toast.success("Counter-offer draft ready.") }
    );
  }, [role, location, roleOk, baseOk, baseNum, matchNum, counter]);

  const runCompare = React.useCallback(() => {
    if (!roleOk) return;
    const offers = offerLabels
      .split("\n")
      .map((l) => l.trim())
      .filter(Boolean)
      .map((label, i) => ({ label, base: baseNum || 0, bonus: 0 }));
    if (!offers.length) {
      toast.error(t("offers.nameOneOffer"));
      return;
    }
    compare.mutate(
      {
        role: role.trim(),
        location: location.trim() || undefined,
        currency,
        matchScore: matchNum,
        offers,
      },
      { onSuccess: () => toast.success("Offers compared.") }
    );
  }, [role, location, roleOk, baseNum, matchNum, offerLabels, compare]);

  const bench = benchmark.data;
  const plan = negotiate.data;
  const draft = counter.data;
  const comparison = compare.data;

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <PageHeader
        title={t("offers.title")}
        description={t("offers.description")}
      />

      {/* The question */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">{t("offers.roleAndOffer")}</CardTitle>
          <CardDescription>
            One question drives all four answers: what is the role, and what is on the table.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="offer-role">{t("offers.role")}</Label>
              <Input
                id="offer-role"
                value={role}
                onChange={(e) => setRole(e.target.value)}
                placeholder="e.g. Senior Backend Engineer (Java)"
                autoComplete="off"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="offer-location">{t("offers.location")}</Label>
              <Input
                id="offer-location"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                placeholder="e.g. Shanghai"
                autoComplete="off"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="offer-base">{t("offers.offerBase")}</Label>
              <Input
                id="offer-base"
                type="number"
                value={offerBase}
                onChange={(e) => setOfferBase(e.target.value)}
                placeholder="e.g. 400000"
                autoComplete="off"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="offer-match">{t("offers.yourMatch")}</Label>
              <Input
                id="offer-match"
                type="number"
                value={matchScore}
                onChange={(e) => setMatchScore(e.target.value)}
                placeholder="e.g. 82"
                autoComplete="off"
              />
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button
              variant="ai"
              size="sm"
              loading={benchmark.isPending}
              disabled={!roleOk}
              onClick={runBenchmark}
            >
              <BadgeDollarSign aria-hidden />
              {t("offers.benchmark")}
            </Button>
            <Button
              variant="outline"
              size="sm"
              loading={negotiate.isPending}
              disabled={!roleOk || !baseOk}
              onClick={runNegotiate}
            >
              <Handshake aria-hidden />
              {t("offers.coachMe")}
            </Button>
            <Button
              variant="outline"
              size="sm"
              loading={counter.isPending}
              disabled={!roleOk || !baseOk}
              onClick={runCounter}
            >
              <Target aria-hidden />
              {t("offers.draftCounter")}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Benchmark */}
      {bench && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">{t("offers.whatTheMarketPays")}</CardTitle>
            <CardDescription>
              {bench.sampleSize ?? 0} matching postings
              {bench.location ? ` in ${bench.location}` : ""}.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <BarChart
              data={(["p25", "p50", "p75"] as const).map((k) => ({
                label: k,
                value: bench.percentiles?.[k] ?? 0,
                // The median is the one the offer is compared against, so it
                // carries the accent; the tails are the range around it.
                tone: k === "p50" ? ("primary" as const) : ("muted" as const),
              }))}
              valueFormat={(v) => formatSalary(v, v, bench.currency) ?? "—"}
            />
            {bench.note && <p className="mt-3 text-xs text-muted-foreground">{bench.note}</p>}
          </CardContent>
        </Card>
      )}

      {/* Negotiation plan */}
      {plan && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">{t("offers.negotiationPlan")}</CardTitle>
            <CardDescription>{t("offers.againstTheMarket")}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center gap-2">
              <Badge
                variant={plan.verdict === "above_market" ? "success" : plan.verdict === "below_market" ? "warning" : "secondary"}
                className="capitalize"
              >
                {(plan.verdict ?? "unknown").replace(/_/g, " ")}
              </Badge>
              {plan.leverage && <p className="text-sm">{plan.leverage}</p>}
            </div>
            {(plan.talkingPoints ?? []).length > 0 && (
              <>
                <Separator />
                <ul className="space-y-1.5">
                  {(plan.talkingPoints ?? []).map((point, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm">
                      <span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-primary" aria-hidden />
                      {point}
                    </li>
                  ))}
                </ul>
              </>
            )}
          </CardContent>
        </Card>
      )}

      {/* Counter-offer draft */}
      {draft && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">{t("offers.counterOfferDraft")}</CardTitle>
            <CardDescription>
              {draft.anchor
                ? `Anchor at ${formatSalary(draft.anchor, draft.anchor, currency)}.`
                : "The anchor the engine computed."}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {(draft.reasons ?? []).length > 0 && (
              <ul className="space-y-1.5">
                {(draft.reasons ?? []).map((reason, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm">
                    <span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-primary" aria-hidden />
                    {reason}
                  </li>
                ))}
              </ul>
            )}
            {draft.script && (
              <Textarea
                readOnly
                value={draft.script}
                rows={4}
                aria-label={t("offers.counterOfferScript")}
                className="text-sm"
              />
            )}
          </CardContent>
        </Card>
      )}

      {/* Comparison */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">{t("offers.compareOffers")}</CardTitle>
          <CardDescription>
            One offer per line. The engine ranks them by total compensation, with any
            equity annualized over its vest.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="space-y-2">
            <Label htmlFor="offer-labels">{t("offers.offerLabels")}</Label>
            <Textarea
              id="offer-labels"
              value={offerLabels}
              onChange={(e) => setOfferLabels(e.target.value)}
              rows={3}
              placeholder={"Offer A\nOffer B"}
            />
          </div>
          <Button
            variant="outline"
            size="sm"
            loading={compare.isPending}
            disabled={!roleOk}
            onClick={runCompare}
          >
            <Scale aria-hidden />
            {t("offers.compare")}
          </Button>

          {comparison && (
            <>
              {(comparison.rows ?? []).length > 0 ? (
                <div className="space-y-3">
                  <BarChart
                    data={comparison.rows!.map((row) => ({
                      label: row.label ?? "—",
                      value: row.totalComp ?? 0,
                      detail: row.assessment?.verdict?.replace(/_/g, " "),
                      tone:
                        row.label && comparison.best?.label === row.label
                          ? "success"
                          : "primary",
                    }))}
                    valueFormat={(v) => formatSalary(v, v, currency) ?? "—"}
                  />
                  {comparison.best?.label && (
                    <p className="text-xs text-muted-foreground">
                      {comparison.best.label} leads on total compensation.
                    </p>
                  )}
                </div>
              ) : (
                <EmptyState
                  icon={<Scale aria-hidden />}
                  title={t("offers.noComparison")}
                  description={t("offers.nameOneOffer")}
                />
              )}
              {(comparison.notes ?? []).length > 0 && (
                <p className="text-xs text-muted-foreground">
                  {comparison.notes!.join(" ")}
                </p>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
