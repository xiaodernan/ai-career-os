"use client";

import * as React from "react";
import { Plus, RotateCcw, Scale, Trash2, Trophy } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useOfferShelf } from "@/lib/hooks/resources";
import { useLocale } from "@/lib/i18n/locale-context";
import {
  LEDGER_MAX_CRITERIA,
  LEDGER_MAX_SCORE,
  addCriterion,
  clearLedger,
  computeLedger,
  ledgerIsDirty,
  loadLedger,
  removeCriterion,
  saveLedger,
  setScore,
  setWeight,
  starterLedger,
  type LedgerState,
} from "@/lib/offers/decision-ledger";

/**
 * The decision ledger (Epic 215) — the weights only the reader can set.
 *
 * The shelf ranks offers by one deterministic number: total compensation.
 * The market knows what each row pays; it cannot know what each row does to
 * a life. The ledger is the reader's own answer: six starter criteria the
 * reader can re-weight, rename-by-adding, or score per offer — persisted in
 * the reader's browser, computed on the client, sent nowhere. A recorded 0
 * is a real score ("this fails the criterion"), never a blank in disguise.
 *
 * Layout contract: table on narrow-scroll for phones, role=status verdict,
 * no timers, reduced motion inherited from the house blanket rule.
 */
export function OfferDecisionLedger() {
  const { t } = useLocale();
  const shelf = useOfferShelf();
  const offers = React.useMemo(() => shelf.data?.items ?? [], [shelf.data]);
  const offerIds = React.useMemo(() => offers.map((row) => row.id), [offers]);

  const [state, setState] = React.useState<LedgerState>(() => starterLedger());
  const [hydrated, setHydrated] = React.useState(false);
  const [draft, setDraft] = React.useState("");

  React.useEffect(() => {
    setState(loadLedger());
    setHydrated(true);
  }, []);

  React.useEffect(() => {
    if (hydrated) saveLedger(state);
  }, [state, hydrated]);

  const computation = computeLedger(offerIds, state);
  const rows = computation.rows;
  const anyScored = rows.some((row) => row.scored > 0);
  const dirty = ledgerIsDirty(state);
  const leaderIds = new Set(computation.leaderIds);

  const criterionLabel = (id: string, custom: boolean, label: string) =>
    custom ? label : t(`offers.ledgerCriterion_${id}`);

  const handleAdd = () => {
    const next = addCriterion(state, draft);
    if (!next) {
      toast.info(t("offers.ledgerMaxReached"));
      return;
    }
    setState(next);
    setDraft("");
  };

  const handleReset = () => {
    clearLedger();
    setState(starterLedger());
    toast.success(t("offers.ledgerResetDone"));
  };

  const offerLabelById = new Map(offers.map((row) => [row.id, row.label]));
  const leaderLabels = computation.leaderIds.map((id) => offerLabelById.get(id) ?? id);
  const verdictMax = rows[0]?.max ?? 0;
  const verdictTotal = rows.length > 0 ? Math.max(...rows.map((row) => row.total)) : 0;

  return (
    <Card
      data-testid="decision-ledger"
      className="overflow-hidden border-primary/20 bg-gradient-to-br from-violet-50/50 via-card to-card shadow-card print:break-inside-avoid"
    >
      <CardHeader className="flex flex-row items-start gap-4 space-y-0">
        <div className="flex size-10 shrink-0 items-center justify-center rounded-xl border border-primary/25 bg-primary/10 text-primary">
          <Scale aria-hidden className="size-5" />
        </div>
        <div className="min-w-0">
          <CardTitle className="text-base">{t("offers.ledgerTitle")}</CardTitle>
          <CardDescription>{t("offers.ledgerDescription")}</CardDescription>
        </div>
        {dirty && (
          <Button
            variant="ghost"
            size="sm"
            className="ml-auto shrink-0"
            onClick={handleReset}
            aria-label={t("offers.ledgerReset")}
          >
            <RotateCcw aria-hidden className="size-4" />
            <span className="hidden sm:inline">{t("offers.ledgerReset")}</span>
          </Button>
        )}
      </CardHeader>
      <CardContent className="space-y-4">
        {shelf.isPending && (
          <div className="space-y-2" aria-hidden="true">
            <div className="h-9 w-full animate-pulse rounded-lg bg-muted/40" />
            <div className="h-9 w-full animate-pulse rounded-lg bg-muted/40" />
            <div className="h-9 w-2/3 animate-pulse rounded-lg bg-muted/40" />
          </div>
        )}

        {!shelf.isPending && offers.length === 0 && (
          <p className="text-sm text-muted-foreground">{t("offers.ledgerEmptyShelf")}</p>
        )}

        {!shelf.isPending && offers.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-sm">
              <caption className="sr-only">{t("offers.ledgerTableCaption")}</caption>
              <thead>
                <tr>
                  <th scope="col" className="pb-2 pr-2 text-left text-2xs font-semibold uppercase tracking-wider text-muted-foreground">
                    {t("offers.ledgerCriterionCol")}
                  </th>
                  <th scope="col" className="pb-2 pr-2 text-left text-2xs font-semibold uppercase tracking-wider text-muted-foreground">
                    {t("offers.ledgerWeight")}
                  </th>
                  {offers.map((row) => (
                    <th
                      key={row.id}
                      scope="col"
                      className="pb-2 px-1 text-center align-bottom"
                    >
                      <span
                        className="mx-auto block max-w-[10rem] truncate text-xs font-medium"
                        title={row.label}
                      >
                        {row.label}
                      </span>
                      {anyScored && leaderIds.has(row.id) && (
                        <Trophy aria-hidden className="mx-auto mt-0.5 size-3.5 text-warning" />
                      )}
                    </th>
                  ))}
                  <th scope="col" className="pb-2 pl-2 text-right text-2xs font-semibold uppercase tracking-wider text-muted-foreground">
                    <span className="sr-only">{t("offers.ledgerRemoveCriterion")}</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {state.criteria.map((criterion) => {
                  const name = criterionLabel(criterion.id, criterion.custom, criterion.label);
                  return (
                    <tr key={criterion.id} className="border-t border-border/50 align-middle">
                      <th scope="row" className="max-w-[12rem] py-2 pr-2 text-left text-xs font-medium leading-snug">
                        {name}
                      </th>
                      <td className="py-2 pr-2">
                        <Select
                          value={String(criterion.weight)}
                          onValueChange={(value) => setState(setWeight(state, criterion.id, Number(value)))}
                        >
                          <SelectTrigger
                            className="h-9 w-[8.5rem] text-2xs"
                            aria-label={t("offers.ledgerWeightFor", { criterion: name })}
                          >
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {[0, 1, 2, 3, 4, 5].map((weight) => (
                              <SelectItem key={weight} value={String(weight)}>
                                {t(`offers.ledgerWeight_${weight}`)}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </td>
                      {offers.map((offer) => {
                        const score = state.scores[offer.id]?.[criterion.id];
                        return (
                          <td key={offer.id} className="py-2 px-1 text-center">
                            <Input
                              type="number"
                              min={0}
                              max={LEDGER_MAX_SCORE}
                              step={1}
                              inputMode="numeric"
                              aria-label={t("offers.ledgerOfferScore", { criterion: name, offer: offer.label })}
                              className="h-9 w-14 px-1 text-center text-xs tabular-nums"
                              value={score === undefined ? "" : String(score)}
                              placeholder="–"
                              onChange={(event) =>
                                setState(setScore(state, offer.id, criterion.id, event.target.value))
                              }
                            />
                          </td>
                        );
                      })}
                      <td className="py-2 pl-2 text-right">
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          aria-label={t("offers.ledgerRemoveCriterion")}
                          onClick={() => setState(removeCriterion(state, criterion.id))}
                        >
                          <Trash2 aria-hidden className="size-3.5 text-muted-foreground" />
                        </Button>
                      </td>
                    </tr>
                  );
                })}
                <tr className="border-t-2 border-border">
                  <th scope="row" className="py-3 pr-2 text-left text-2xs font-semibold uppercase tracking-wider text-muted-foreground">
                    {t("offers.ledgerTotal")}
                  </th>
                  <td className="py-3 pr-2" />
                  {rows.map((row) => (
                    <td key={row.offerId} className="py-3 px-1 text-center align-top">
                      <span className="block text-base font-semibold tabular-nums leading-none">
                        {row.max > 0 ? row.total : "–"}
                      </span>
                      <span className="mt-1 block text-2xs tabular-nums text-muted-foreground">
                        {row.max > 0 ? t("offers.ledgerTotalOf", { total: row.total, max: row.max }) : ""}
                      </span>
                    </td>
                  ))}
                  <td className="py-3 pl-2" />
                </tr>
              </tbody>
            </table>

            <form
              className="mt-3 flex flex-wrap items-end gap-2"
              onSubmit={(event) => {
                event.preventDefault();
                handleAdd();
              }}
            >
              <div className="min-w-0 flex-1 space-y-1">
                <Label htmlFor="ledger-new-criterion" className="text-2xs text-muted-foreground">
                  {t("offers.ledgerAddCriterion")}
                </Label>
                <Input
                  id="ledger-new-criterion"
                  value={draft}
                  onChange={(event) => setDraft(event.target.value)}
                  placeholder={t("offers.ledgerAddPlaceholder")}
                  autoComplete="off"
                  maxLength={120}
                  disabled={state.criteria.length >= LEDGER_MAX_CRITERIA}
                />
              </div>
              <Button type="submit" variant="outline" size="sm" disabled={!draft.trim() || state.criteria.length >= LEDGER_MAX_CRITERIA}>
                <Plus aria-hidden className="size-4" />
                {t("offers.ledgerAddButton")}
              </Button>
            </form>

            <p role="status" aria-live="polite" className="mt-3 text-xs leading-relaxed text-foreground/90">
              {!anyScored || leaderIds.size === 0 ? (
                t("offers.ledgerNeedScores")
              ) : leaderIds.size === 1 ? (
                <span className="inline-flex flex-wrap items-center gap-1.5">
                  <Trophy aria-hidden className="size-3.5 text-warning" />
                  {t("offers.ledgerLeader", {
                    label: leaderLabels[0],
                    total: verdictTotal,
                    max: verdictMax,
                  })}
                </span>
              ) : (
                t("offers.ledgerTie", {
                  labels: leaderLabels.join(" · "),
                  total: verdictTotal,
                  max: verdictMax,
                })
              )}
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
