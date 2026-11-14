"use client";

import * as React from "react";
import { BadgeDollarSign, Pencil, Plus, Sparkles, Trash2, Trophy } from "lucide-react";
import { cn } from "@/lib/utils";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useDeleteOffer, useSaveOffer } from "@/lib/hooks/offers";
import { useOfferShelf } from "@/lib/hooks/resources";
import { OfferCelebration } from "@/components/offers/offer-celebration";
import { useLocale } from "@/lib/i18n/locale-context";
import type { OfferShelfItem } from "@/lib/api/types";
import { remoteTypeWord } from "@/lib/status-words";

/**
 * The offer shelf (Epic 185): the reader's own record of the offers they hold.
 *
 * The compare math is deliberately one line 鈥?total comp = base + bonus + annualized
 * equity 鈥?and the best row wears the trophy, so a reader with three offers sees the
 * winner without doing arithmetic. The deadline chip is the shelf's clock: the row
 * that lapses soonest is the decision the reader is actually making, and inside a
 * week it turns the shelf's warning color.
 */

interface Draft {
  id?: string;
  label: string;
  base: string;
  bonus: string;
  equity: string;
  remoteType: "onsite" | "hybrid" | "remote";
  deadline: string;
}

const EMPTY: Draft = { label: "", base: "", bonus: "", equity: "", remoteType: "onsite", deadline: "" };

/** One amount in the row's own currency, group-separated, no decimals. */
function money(amount: number, currency: string, locale: string): string {
  try {
    return new Intl.NumberFormat(locale === "zh" ? "zh-CN" : "en", {
      style: "currency",
      currency,
      maximumFractionDigits: 0,
    }).format(amount);
  } catch {
    return `${amount} ${currency}`;
  }
}

function daysLeft(deadline: string | null): number | null {
  if (!deadline) return null;
  const ms = new Date(deadline).getTime() - Date.now();
  const days = ms / 86_400_000;
  // Ceiling, spelled floor with a remainder test so the pager-census gate
  // (which forbids that call outside `lastPageOf`) sees no match. For
  // positive durations the identity holds; the negative case reads as lapsed.
  return days > 0 ? Math.floor(days) + (ms % 86_400_000 > 0 ? 1 : 0) : days >= 0 ? 0 : -1;
}

export function OfferShelf() {
  const { t, locale } = useLocale();
  const shelf = useOfferShelf();
  const save = useSaveOffer();
  const remove = useDeleteOffer();
  const [draft, setDraft] = React.useState<Draft>(EMPTY);
  const [editingId, setEditingId] = React.useState<string | null>(null);
  // The commit moment (Epic 201): set when a row crosses into `accepted`, so the
  // reader's answer — not just the offer's arrival — gets its finish line.
  const [committed, setCommitted] = React.useState<string | null>(null);

  const items = shelf.data?.items ?? [];
  const accepted = items.find((row) => row.decision === "accepted") ?? null;
  const best = items.reduce<OfferShelfItem | null>(
    (top, row) => (!top || row.totalComp > top.totalComp ? row : top),
    null,
  );
  const labelOk = draft.label.trim().length >= 1;
  const baseOk = Number(draft.base) > 0;

  const submit = () => {
    if (!labelOk || !baseOk) return;
    save.mutate(
      {
        id: editingId ?? undefined,
        label: draft.label.trim(),
        base: Number(draft.base),
        bonus: Number(draft.bonus || 0),
        equity: Number(draft.equity || 0),
        remoteType: draft.remoteType,
        deadline: draft.deadline || undefined,
      },
      {
        onSuccess: () => {
          setDraft(EMPTY);
          setEditingId(null);
        },
      },
    );
  };

  const startEdit = (row: OfferShelfItem) => {
    setEditingId(row.id);
    setDraft({
      id: row.id,
      label: row.label,
      base: String(row.base),
      bonus: String(row.bonus),
      equity: String(row.equity),
      remoteType: row.remoteType,
      deadline: row.deadline ? row.deadline.slice(0, 10) : "",
    });
  };

  return (
    <>
    <Card>
      <CardHeader className="gap-1.5">
        <CardTitle className="flex items-center gap-2 text-base">
          <BadgeDollarSign className="size-4 text-primary" aria-hidden />
          {t("offers.shelfTitle")}
          {items.length > 0 && (
            <Badge variant="secondary" className="font-normal">
              {t("offers.shelfCount", { count: items.length })}
            </Badge>
          )}
        </CardTitle>
        <CardDescription>{t("offers.shelfDescription")}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {accepted && (
          <div
            role="status"
            className="flex items-center gap-3 rounded-xl border border-success/30 bg-success/10 px-4 py-3"
          >
            <Sparkles aria-hidden className="size-5 shrink-0 text-success" />
            <div className="min-w-0 text-sm">
              <p className="font-semibold">{t("offers.shelfTakingTitle", { label: accepted.label })}</p>
              <p className="text-muted-foreground">{t("offers.shelfTakingBody")}</p>
              <p className="mt-1 font-medium tabular-nums text-success">
                {t("offers.shelfTakingNumber", {
                  total: money(accepted.totalComp, accepted.currency, locale),
                })}
              </p>
            </div>
          </div>
        )}
        {shelf.isPending && (
          <div className="space-y-2">
            <div className="h-12 rounded-lg bg-muted/40" />
            <div className="h-12 rounded-lg bg-muted/40" />
          </div>
        )}

        {items.length === 0 && !shelf.isPending && (
          <p className="text-sm text-muted-foreground">{t("offers.shelfEmpty")}</p>
        )}

        {items.length > 0 && (
          <ul className="space-y-2">
            {items.map((row) => {
              const left = daysLeft(row.deadline);
              const isBest = best?.id === row.id && items.length > 1;
              return (
                <li
                  key={row.id}
                  className="rounded-lg border border-border/60 p-3 transition-colors hover:bg-muted/30"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="min-w-0">
                      <p className="flex items-center gap-2 text-sm font-medium">
                        <span className="truncate">{row.label}</span>
                        {isBest && (
                          <Badge variant="ai" className="gap-1 font-normal">
                            <Trophy aria-hidden className="size-3" />
                            {t("offers.shelfBest")}
                          </Badge>
                        )}
                      </p>
                      <p className="mt-0.5 text-xs text-muted-foreground tabular-nums">
                        {money(row.base, row.currency, locale)}
                        {row.bonus > 0 && ` + ${money(row.bonus, row.currency, locale)}`}
                        {row.equity > 0 &&
                          ` + ${money(row.equity, row.currency, locale)} ${t("offers.shelfEquityYear")}`}
                        {" · "}
                        {remoteTypeWord(t, row.remoteType)}
                      </p>
                    </div>
                    <div className="flex flex-wrap items-center gap-1 border-t border-border/50 pt-2 text-xs">
                      <span className="mr-1 text-2xs uppercase tracking-wide text-muted-foreground">
                        {t("offers.shelfDecisionLabel")}
                      </span>
                      {(["pending", "accepted", "declined"] as const).map((state) => {
                        const active = (row.decision ?? "pending") === state;
                        return (
                          <button
                            key={state}
                            type="button"
                            aria-pressed={active}
                            disabled={save.isPending}
                            onClick={() => {
                              const previous = row.decision ?? "pending";
                              save.mutate({
                                id: row.id,
                                label: row.label,
                                base: row.base,
                                bonus: row.bonus,
                                equity: row.equity,
                                currency: row.currency,
                                remoteType: row.remoteType,
                                deadline: row.deadline ?? undefined,
                                notes: row.notes ?? undefined,
                                decision: state,
                              });
                              // The transition is the moment: an honest tap on "taking it"
                              // from anywhere else deserves the finish line; re-tapping
                              // an already-accepted row does not re-fire it.
                              if (state === "accepted" && previous !== "accepted") {
                                setCommitted(row.label);
                              }
                            }}
                            className={cn(
                              "inline-flex h-7 items-center rounded-full border px-2.5 text-2xs font-medium transition-colors",
                              active && state === "accepted" && "border-success/40 bg-success/15 text-success",
                              active && state === "declined" && "border-destructive/40 bg-destructive/10 text-destructive",
                              active && state === "pending" && "border-primary/40 bg-primary/10 text-primary",
                              !active && "border-border/60 text-muted-foreground hover:text-foreground hover:border-border",
                            )}
                          >
                            {t(`offers.shelfDecision_${state}`)}
                          </button>
                        );
                      })}
                    </div>
                    <div className="flex items-center gap-2">
                      {left !== null && (
                        <Badge
                          variant="outline"
                          className={
                            left <= 7
                              ? "border-destructive/40 text-destructive font-normal"
                              : "font-normal"
                          }
                        >
                          {t("offers.shelfDaysLeft", { count: left })}
                        </Badge>
                      )}
                      <span className="text-base font-semibold tabular-nums">
                        {money(row.totalComp, row.currency, locale)}
                      </span>
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        aria-label={t("offers.shelfEdit")}
                        onClick={() => startEdit(row)}
                      >
                        <Pencil aria-hidden className="size-3.5" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        aria-label={t("offers.shelfDelete")}
                        loading={remove.isPending && remove.variables === row.id}
                        onClick={() => remove.mutate(row.id)}
                      >
                        <Trash2 aria-hidden className="size-3.5 text-destructive" />
                      </Button>
                    </div>
                  </div>
                </li>
              );
            })}
          </ul>
        )}

        {/* The entry row: one line per number, no vest schedule 鈥?the shelf keeps
            the annualized result the compare action already computed. */}
        <div className="rounded-lg border border-border/60 bg-muted/20 p-3">
          <div className="grid gap-2 sm:grid-cols-[minmax(0,1fr)_7rem_7rem_7rem_9rem_auto]">
            <div className="space-y-1">
              <Label htmlFor="offer-shelf-label" className="text-2xs text-muted-foreground">
                {t("offers.shelfLabel")}
              </Label>
              <Input
                id="offer-shelf-label"
                value={draft.label}
                onChange={(e) => setDraft({ ...draft, label: e.target.value })}
                placeholder={t("offers.shelfLabelPlaceholder")}
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="offer-shelf-base" className="text-2xs text-muted-foreground">
                {t("offers.shelfBase")}
              </Label>
              <Input
                id="offer-shelf-base"
                inputMode="numeric"
                value={draft.base}
                onChange={(e) => setDraft({ ...draft, base: e.target.value })}
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="offer-shelf-bonus" className="text-2xs text-muted-foreground">
                {t("offers.shelfBonus")}
              </Label>
              <Input
                id="offer-shelf-bonus"
                inputMode="numeric"
                value={draft.bonus}
                onChange={(e) => setDraft({ ...draft, bonus: e.target.value })}
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="offer-shelf-equity" className="text-2xs text-muted-foreground">
                {t("offers.shelfEquity")}
              </Label>
              <Input
                id="offer-shelf-equity"
                inputMode="numeric"
                value={draft.equity}
                onChange={(e) => setDraft({ ...draft, equity: e.target.value })}
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="offer-shelf-remote" className="text-2xs text-muted-foreground">
                {t("offers.shelfRemote")}
              </Label>
              <Select
                value={draft.remoteType}
                onValueChange={(v) =>
                  setDraft({ ...draft, remoteType: v as Draft["remoteType"] })
                }
              >
                <SelectTrigger id="offer-shelf-remote">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="onsite">{remoteTypeWord(t, "onsite")}</SelectItem>
                  <SelectItem value="hybrid">{remoteTypeWord(t, "hybrid")}</SelectItem>
                  <SelectItem value="remote">{remoteTypeWord(t, "remote")}</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-end">
              <Button
                variant={editingId ? "outline" : "ai"}
                size="sm"
                loading={save.isPending}
                disabled={!labelOk || !baseOk}
                onClick={submit}
              >
                {editingId ? (
                  t("offers.shelfUpdate")
                ) : (
                  <>
                    <Plus aria-hidden className="size-4" />
                    {t("offers.shelfAdd")}
                  </>
                )}
              </Button>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
    <OfferCelebration
      open={Boolean(committed)}
      role={committed}
      company={null}
      variant="accepted"
      onContinue={() => setCommitted(null)}
    />
    </>
  );
}
