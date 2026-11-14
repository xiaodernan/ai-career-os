"use client";

import * as React from "react";
import { CalendarRange, Check, RotateCcw, Trophy } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useLocale } from "@/lib/i18n/locale-context";
import { useOfferShelf } from "@/lib/hooks/resources";

/**
 * OfferFirstQuarter — the plan the packet opens onto (Epic 209).
 *
 * The day-one packet ends at the ceremony: seven chores between "yes" and day one.
 * The quarter that follows is where new hires quietly decide whether they are
 * staying for ten years or twelve months, and nobody hands them the script.
 * This card is that script: three acts, sixteen quiet ticks, the same shape as
 * the packet that precedes it — persistent only in the reader's browser, keyed
 * to the accepted row, no network, no fake precision.
 *
 * The three acts earn their names from the way the best early weeks actually go:
 *
 *   - Days 1-30 (land): learn the place, find the three people whose work wins,
 *     ship one small thing visibly well, pin the 1:1 cadence before you need it.
 *   - Days 31-60 (own): one user-facing surface that is yours end-to-end, the
 *     first honest risk in writing, feedback you would rather not hear.
 *   - Days 61-90 (lift): the promised outcome with the two-line story, teach one
 *     thing cold to the team, update the resume while the year is fresh.
 *
 * The copy is advice, not claims — nothing here says what this product does. The
 * layout keeps the house contract: ringed disc, promise line, transform/opacity
 * only, no timers, reduced motion respected through the blanket rule.
 */

const ACTS: { id: string; titleKey: string; blurbKey: string; items: string[] }[] = [
  {
    id: "land",
    titleKey: "offers.quarterActLand",
    blurbKey: "offers.quarterLandBlurb",
    items: [
      "quarterLand1", "quarterLand2", "quarterLand3",
      "quarterLand4", "quarterLand5", "quarterLand6",
    ],
  },
  {
    id: "own",
    titleKey: "offers.quarterActOwn",
    blurbKey: "offers.quarterOwnBlurb",
    items: [
      "quarterOwn1", "quarterOwn2", "quarterOwn3",
      "quarterOwn4", "quarterOwn5", "quarterOwn6",
    ],
  },
  {
    id: "lift",
    titleKey: "offers.quarterActLift",
    blurbKey: "offers.quarterLiftBlurb",
    items: [
      "quarterLift1", "quarterLift2", "quarterLift3",
      "quarterLift4", "quarterLift5", "quarterLift6",
    ],
  },
];

const STORAGE_PREFIX = "careeros.quarter.";
const TOTAL = ACTS.reduce((n, act) => n + act.items.length, 0);

function readState(offerId: string | null): Record<string, boolean> {
  if (!offerId || typeof window === "undefined") return {};
  try {
    const raw = window.localStorage.getItem(STORAGE_PREFIX + offerId);
    return raw ? (JSON.parse(raw) as Record<string, boolean>) : {};
  } catch {
    return {};
  }
}

export function OfferFirstQuarter() {
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

  const checked = Object.values(done).filter(Boolean).length;
  const pct = Math.round((checked / TOTAL) * 100);
  const allDone = checked === TOTAL;

  const toggle = (id: string) => {
    const next = { ...done, [id]: !done[id] };
    setDone(next);
    try {
      window.localStorage.setItem(STORAGE_PREFIX + accepted.id, JSON.stringify(next));
    } catch {
      // best effort, visible state still flips
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
      data-testid="first-quarter"
      className="overflow-hidden border-primary/20 bg-gradient-to-br from-primary/5 via-card to-card shadow-card scroll-mt-24"
    >
      <CardHeader className="flex flex-row items-start gap-4 space-y-0">
        <div className="flex size-10 shrink-0 items-center justify-center rounded-xl border border-primary/25 bg-primary/10 text-primary">
          <CalendarRange aria-hidden className="size-5" />
        </div>
        <div className="min-w-0">
          <CardTitle className="text-base">{t("offers.quarterTitle", { role: accepted.label })}</CardTitle>
          <CardDescription>{t("offers.quarterDescription")}</CardDescription>
        </div>
        {checked > 0 && (
          <Button variant="ghost" size="icon-sm" onClick={reset} aria-label={t("offers.quarterReset")}>
            <RotateCcw aria-hidden className="size-4" />
          </Button>
        )}
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="flex items-center justify-between gap-3 text-xs tabular-nums text-muted-foreground">
          <span>{t("offers.quarterCount", { done: checked, total: TOTAL })}</span>
          <div
            className="h-1.5 w-36 overflow-hidden rounded-full bg-muted"
            role="progressbar"
            aria-valuemin={0}
            aria-valuemax={TOTAL}
            aria-valuenow={checked}
            aria-label={t("offers.quarterCount", { done: checked, total: TOTAL })}
          >
            <div
              className="h-full rounded-full bg-primary transition-[width] duration-300"
              style={{ width: `${pct}%` }}
            />
          </div>
        </div>
        <div className="grid gap-5 md:grid-cols-3">
          {ACTS.map((act) => {
            const actChecked = act.items.filter((id) => done[id]).length;
            return (
              <div key={act.id} className="space-y-2">
                <div className="flex items-baseline justify-between gap-2 border-b border-border/60 pb-1.5">
                  <div>
                    <p className="text-2xs font-semibold uppercase tracking-wide text-primary">
                      {t(act.titleKey)}
                    </p>
                    <p className="mt-0.5 text-2xs text-muted-foreground">{t(act.blurbKey)}</p>
                  </div>
                  <span className="text-2xs tabular-nums text-muted-foreground">
                    {actChecked}/{act.items.length}
                  </span>
                </div>
                <ul className="space-y-1.5">
                  {act.items.map((id) => {
                    const isDone = Boolean(done[id]);
                    return (
                      <li key={id}>
                        <button
                          type="button"
                          onClick={() => toggle(id)}
                          aria-pressed={isDone}
                          className={cn(
                            "flex w-full items-start gap-2 rounded-lg px-2 py-1.5 text-left text-xs leading-snug transition-colors duration-150 focus-visible:ring-[3px] focus-visible:ring-primary/30",
                            isDone ? "text-muted-foreground" : "text-foreground hover:bg-accent/40"
                          )}
                        >
                          <span
                            aria-hidden
                            className={cn(
                              "mt-0.5 flex size-4 shrink-0 items-center justify-center rounded border transition-colors",
                              isDone
                                ? "border-success/50 bg-success/15 text-success"
                                : "border-border/70"
                            )}
                          >
                            {isDone ? <Check className="size-3" aria-hidden /> : null}
                          </span>
                          <span className={cn(isDone && "line-through decoration-muted-foreground/60")}>
                            {t(`offers.${id}`)}
                          </span>
                        </button>
                      </li>
                    );
                  })}
                </ul>
              </div>
            );
          })}
        </div>
        {allDone && (
          <div className="flex items-center gap-2 rounded-lg border border-success/30 bg-success/10 px-4 py-3 text-sm text-success">
            <Trophy aria-hidden className="size-4 shrink-0" />
            {t("offers.quarterAllDone")}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
