"use client";

import { ArrowRight, Sparkles } from "lucide-react";

import { cn } from "@/lib/utils";
import { useLocale } from "@/lib/i18n/locale-context";

/**
 * The front-door illustration, shared by the landing hero and the auth panel.
 *
 * A static picture of the product at work -- the board at a glance, a match
 * ring, the copilot's doorway -- drawn from the design tokens, not a
 * screenshot. Both anonymous surfaces sell the same claim, and both deserve
 * the same proof; a second copy of this would drift from the first.
 *
 * Every inner node is decorative and aria-hidden behind one honest label on
 * the figure; the surrounding copy stays the caller's to choose.
 */
export function ProductPreview({ className }: { className?: string }) {
  const { t } = useLocale();

  return (
    <figure
      role="img"
      aria-label={t("landing.preview.label")}
      className={cn("animate-fade-up text-left", className)}
    >
      <div className="overflow-hidden rounded-2xl border border-border/70 bg-card shadow-pop">
        {/* window chrome */}
        <div
          className="flex items-center gap-1.5 border-b border-border/60 bg-muted/40 px-4 py-2.5"
          aria-hidden
        >
          <span className="size-2.5 rounded-full bg-red-400/70" />
          <span className="size-2.5 rounded-full bg-amber-400/70" />
          <span className="size-2.5 rounded-full bg-emerald-400/70" />
          <span className="ml-2 text-2xs tabular-nums text-muted-foreground">
            careeros.app/applications
          </span>
        </div>
        <div className="grid gap-3 p-4 sm:grid-cols-[minmax(0,1fr)_11rem] sm:p-5">
          {/* the board, at a glance */}
          <div className="grid grid-cols-3 gap-2 sm:gap-3" aria-hidden>
            {[
              { label: t("landing.preview.applied"), count: 3, cards: 2 },
              { label: t("landing.preview.interview"), count: 2, cards: 2 },
              { label: t("landing.preview.offer"), count: 1, cards: 1 },
            ].map((col) => (
              <div
                key={col.label}
                className="flex flex-col gap-2 rounded-xl border border-border/60 bg-muted/30 p-2 sm:p-2.5"
              >
                <div className="flex items-center justify-between px-0.5 text-2xs font-semibold uppercase tracking-wide text-muted-foreground">
                  <span className="truncate">{col.label}</span>
                  <span className="tabular-nums">{col.count}</span>
                </div>
                {Array.from({ length: col.cards }).map((_, i) => (
                  <div
                    key={i}
                    className="space-y-1.5 rounded-lg border border-border/60 bg-background/80 p-2"
                  >
                    <div className="h-2 w-4/5 rounded bg-muted-foreground/25" />
                    <div className="h-2 w-3/5 rounded bg-muted-foreground/20" />
                    <div className="mt-1 flex items-center gap-1 pt-0.5">
                      <div className="h-4 w-10 rounded-full bg-primary/15" />
                      <div className="h-2 w-6 rounded bg-muted-foreground/15" />
                    </div>
                  </div>
                ))}
              </div>
            ))}
          </div>
          {/* the match panel, at a glance; on a narrow panel only the board survives */}
          <div
            className="hidden flex-col items-center justify-center gap-2 rounded-xl border border-border/60 bg-muted/30 p-4 sm:flex"
            aria-hidden
          >
            <div
              className="flex size-20 items-center justify-center rounded-full"
              style={{
                background:
                  "conic-gradient(var(--primary) 0 331deg, color-mix(in oklch, var(--primary) 14%, transparent) 331deg 360deg)",
              }}
            >
              <div className="flex size-16 flex-col items-center justify-center rounded-full bg-card">
                <span className="text-lg font-semibold tabular-nums leading-none">92</span>
                <span className="text-[10px] uppercase tracking-wide text-muted-foreground">
                  {t("landing.preview.match")}
                </span>
              </div>
            </div>
            <div className="w-full space-y-1.5">
              <div className="h-1.5 w-full rounded bg-muted-foreground/20" />
              <div className="h-1.5 w-4/5 rounded bg-muted-foreground/20" />
              <div className="h-1.5 w-3/5 rounded bg-muted-foreground/20" />
            </div>
          </div>
        </div>
        {/* the copilot's doorway */}
        <div
          className="flex items-center gap-2 border-t border-border/60 bg-background/60 px-4 py-3 text-sm text-muted-foreground"
          aria-hidden
        >
          <Sparkles className="size-4 shrink-0 text-primary" />
          <span className="truncate">{t("landing.preview.copilot")}</span>
          <ArrowRight className="ml-auto size-4 shrink-0" />
        </div>
      </div>
    </figure>
  );
}
