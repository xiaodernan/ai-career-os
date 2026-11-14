"use client";

import * as React from "react";
import { Check, PartyPopper, RotateCcw, Sparkles } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useLocale } from "@/lib/i18n/locale-context";
import { useOfferShelf } from "@/lib/hooks/resources";

/**
 * OfferDayOnePacket — the checklist between "they said yes" and "day one".
 *
 * The product earns its keep by getting the reader from posting to an offer;
 * doing nothing between the celebration and the calendar is a lie by omission.
 * This card appears the moment any shelf row is marked accepted, persists the
 * seven steps the reader needs to actually cross the finish line, and
 * immunizes no information of the reader's beyond what they already typed
 * into the shelf (localStorage only). The completion state is the same
 * sentence we told them at the celebration: you already have it all now.
 */

const STEPS: { id: string; key: string }[] = [
  { id: "packetSigned", key: "dayOnePacketSigned" },
  { id: "startDate", key: "dayOneStartDate" },
  { id: "notice", key: "dayOneNotice" },
  { id: "vest", key: "dayOneVest" },
  { id: "benefits", key: "dayOneBenefits" },
  { id: "gear", key: "dayOneGear" },
  { id: "people", key: "dayOnePeople" },
];

const STORAGE_PREFIX = "careeros.dayone.";

function readState(offerId: string | null): Record<string, boolean> {
  if (!offerId || typeof window === "undefined") return {};
  try {
    const raw = window.localStorage.getItem(STORAGE_PREFIX + offerId);
    return raw ? (JSON.parse(raw) as Record<string, boolean>) : {};
  } catch {
    return {};
  }
}

export function OfferDayOnePacket() {
  const { t } = useLocale();
  const shelf = useOfferShelf();
  const accepted = shelf.data?.items.find((row) => row.decision === "accepted") ?? null;
  const [done, setDone] = React.useState<Record<string, boolean>>({});
  const [loaded, setLoaded] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (accepted && loaded !== accepted.id) {
      setDone(readState(accepted.id));
      setLoaded(accepted.id);
    }
  }, [accepted, loaded]);

  if (!accepted) return null;

  const checked = STEPS.filter((s) => done[s.id]).length;
  const total = STEPS.length;
  const pct = Math.round((checked / total) * 100);
  const allDone = checked === total;

  const toggle = (id: string) => {
    const next = { ...done, [id]: !done[id] };
    setDone(next);
    try {
      window.localStorage.setItem(STORAGE_PREFIX + accepted.id, JSON.stringify(next));
    } catch {
      // Object storage is best-effort; the visible state still flips honestly.
    }
  };

  const reset = () => {
    setDone({});
    try {
      window.localStorage.removeItem(STORAGE_PREFIX + accepted.id);
    } catch {
      // ignore
    }
  };

  return (
    <Card
      className="overflow-hidden border-success/30 bg-gradient-to-br from-success/5 via-card to-card shadow-card"
      data-testid="day-one-packet"
    >
      <CardHeader className="flex flex-row items-start gap-4 space-y-0">
        <div className="flex size-10 shrink-0 items-center justify-center rounded-xl border border-success/30 bg-success/10 text-success">
          <Sparkles aria-hidden className="size-5" />
        </div>
        <div className="min-w-0">
          <CardTitle className="text-base">
            {t("offers.dayOneTitle", { role: accepted.label })}
          </CardTitle>
          <CardDescription>{t("offers.dayOneDescription")}</CardDescription>
        </div>
        {checked > 0 && (
          <Button variant="ghost" size="icon-sm" onClick={reset} aria-label={t("offers.dayOneReset")}>
            <RotateCcw aria-hidden className="size-4" />
          </Button>
        )}
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center justify-between gap-3 text-xs tabular-nums text-muted-foreground">
          <span>{t("offers.dayOneCount", { done: checked, total })}</span>
          <span>{pct}%</span>
        </div>
        <div
          role="progressbar"
          aria-valuenow={checked}
          aria-valuemin={0}
          aria-valuemax={total}
          aria-label={t("offers.dayOneCount", { done: checked, total })}
          className="h-2 w-full overflow-hidden rounded-full bg-muted"
        >
          <div
            className="h-full rounded-full bg-gradient-to-r from-success/60 to-success transition-all duration-500 ease-out"
            style={{ width: `${pct}%` }}
          />
        </div>
        <ol className="flex flex-col divide-y divide-border/60">
          {STEPS.map((step) => {
            const isDone = Boolean(done[step.id]);
            return (
              <li key={step.id}>
                <button
                  type="button"
                  aria-pressed={isDone}
                  onClick={() => toggle(step.id)}
                  className="group flex w-full items-start gap-3 rounded-lg py-2.5 text-left outline-none transition-colors hover:bg-muted/40 focus-visible:bg-muted/40"
                >
                  <span
                    aria-hidden
                    className={cn(
                      "mt-0.5 flex size-5 shrink-0 items-center justify-center rounded border transition-all duration-200",
                      isDone
                        ? "border-success/60 bg-success text-success-foreground"
                        : "border-border/70 bg-card group-hover:border-success/50",
                    )}
                  >
                    {isDone && <Check className="size-3" strokeWidth={3} />}
                  </span>
                  <span
                    className={cn(
                      "text-sm leading-snug text-muted-foreground transition-colors",
                      isDone && "text-muted-foreground/60 line-through decoration-muted-foreground/40",
                      !isDone && "group-hover:text-foreground",
                    )}
                  >
                    {t(`offers.${step.key}`)}
                  </span>
                </button>
              </li>
            );
          })}
        </ol>
        {allDone && (
          <div
            role="status"
            className="flex items-center gap-3 rounded-xl border border-success/40 bg-success/10 px-4 py-3 text-sm"
          >
            <PartyPopper aria-hidden className="size-5 shrink-0 text-success" />
            <div>
              <p className="font-semibold">{t("offers.dayOneAllDoneTitle")}</p>
              <p className="text-muted-foreground">{t("offers.dayOneAllDoneBody")}</p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
