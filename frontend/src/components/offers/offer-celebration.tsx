"use client";

import * as React from "react";
import Link from "next/link";
import { Trophy } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useLocale } from "@/lib/i18n/locale-context";

/**
 * OfferCelebration — the one moment in the product that is allowed to feel like
 * a finish line, because it is one.
 *
 * A card just moved to `offer`: the reader's whole loop — parse, match, prepare,
 * rehearse, apply, wait, reply — converged here. The overlay says it once, in
 * the reader's language, with a trophy and a short rain of confetti. No rewards
 * are unlocked, nothing is gamified: the moment belongs to the reader, and the
 * only ask is a single next step (the offers shelf) or a dismissal.
 *
 * The confetti is pure CSS with inline custom properties for the pieces'
 * delay/duration/geometry/color, so it renders the same in tests and in the
 * server's static markup — every piece is in the DOM, `aria-hidden`, flagged by
 * reduced-motion the same way every animation in this codebase is: the blanket
 * media query in globals.css collapses the rain to a still life.
 */
export interface OfferCelebrationProps {
  open: boolean;
  role: string | null;
  company: string | null;
  onContinue: () => void;
  /**
   * Which finish line this overlay marks. `offer` is the card moving to
   * `offer` (the offers shelf is one screen away); `accepted` is the reader's
   * *decision* on the shelf — the moment a preference becomes an answer.
   */
  variant?: "offer" | "accepted";
}

const PIECES = [
  { left: "6%", delay: "0ms", dur: "2600ms", size: 10, hue: "var(--primary)", rot: 25 },
  { left: "11%", delay: "320ms", dur: "2900ms", size: 8, hue: "var(--success)", rot: -30 },
  { left: "17%", delay: "120ms", dur: "2400ms", size: 12, hue: "var(--warning)", rot: 15 },
  { left: "22%", delay: "600ms", dur: "3000ms", size: 9, hue: "var(--primary)", rot: -20 },
  { left: "28%", delay: "240ms", dur: "2700ms", size: 11, hue: "var(--destructive)", rot: 35 },
  { left: "33%", delay: "450ms", dur: "2500ms", size: 7, hue: "var(--success)", rot: -12 },
  { left: "39%", delay: "90ms", dur: "3100ms", size: 12, hue: "var(--warning)", rot: 40 },
  { left: "44%", delay: "530ms", dur: "2650ms", size: 8, hue: "var(--primary)", rot: -35 },
  { left: "50%", delay: "200ms", dur: "2850ms", size: 10, hue: "var(--destructive)", rot: 20 },
  { left: "55%", delay: "380ms", dur: "2350ms", size: 7, hue: "var(--warning)", rot: -28 },
  { left: "61%", delay: "70ms", dur: "2950ms", size: 11, hue: "var(--success)", rot: 18 },
  { left: "66%", delay: "500ms", dur: "2600ms", size: 9, hue: "var(--primary)", rot: -15 },
  { left: "72%", delay: "290ms", dur: "2800ms", size: 12, hue: "var(--warning)", rot: 30 },
  { left: "78%", delay: "150ms", dur: "2450ms", size: 8, hue: "var(--primary)", rot: -38 },
  { left: "84%", delay: "420ms", dur: "3050ms", size: 10, hue: "var(--success)", rot: 12 },
  { left: "89%", delay: "60ms", dur: "2550ms", size: 9, hue: "var(--destructive)", rot: -22 },
  { left: "12%", delay: "700ms", dur: "2650ms", size: 6, hue: "var(--warning)", rot: 45 },
  { left: "30%", delay: "660ms", dur: "2750ms", size: 7, hue: "var(--primary)", rot: -40 },
  { left: "47%", delay: "760ms", dur: "2950ms", size: 6, hue: "var(--success)", rot: 28 },
  { left: "70%", delay: "690ms", dur: "2400ms", size: 7, hue: "var(--destructive)", rot: -18 },
];

export function OfferCelebration({ open, role, company, onContinue, variant = "offer" }: OfferCelebrationProps) {
  const { t } = useLocale();
  if (!open) return null;

  const subtitle =
    role && company
      ? t("offers.celebrationSubtitle", { role, company })
      : role
        ? t("offers.celebrationSubtitleRole", { role })
        : variant === "accepted"
          ? t("offers.committedSubtitleBare")
          : t("offers.celebrationSubtitleBare");

  const title = variant === "accepted" ? t("offers.committedTitle") : t("offers.celebrationTitle");
  const ariaLabel = variant === "accepted" ? t("offers.committedTitle") : t("offers.celebrationTitle");
  const body = variant === "accepted" ? t("offers.committedBody") : t("offers.celebrationBody");
  const primaryLabel = variant === "accepted" ? t("offers.committedShelf") : t("offers.celebrationShelf");
  const primaryHref = variant === "accepted" ? "#day-one-packet" : "/offers";

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={ariaLabel}
      className="fixed inset-0 z-50 flex items-center justify-center overflow-hidden bg-background/70 backdrop-blur-md animate-fade-in"
    >
      {/* The rain. Every piece is decorative; the copy is the content. */}
      <div aria-hidden className="pointer-events-none absolute inset-0">
        {PIECES.map((p, i) => (
          <span
            key={i}
            className="confetti-piece"
            style={{
              left: p.left,
              width: p.size,
              height: p.size * 0.62,
              background: p.hue,
              ["--cf-delay" as string]: p.delay,
              ["--cf-dur" as string]: p.dur,
              ["--cf-rot" as string]: p.rot + "deg",
            } as React.CSSProperties}
          />
        ))}
      </div>

      <div className="relative flex max-w-md flex-col items-center px-6 text-center">
        <div className="flex size-20 animate-scale-in items-center justify-center rounded-2xl border border-primary/25 bg-primary/10 text-primary shadow-glow">
          <Trophy className="size-9" aria-hidden strokeWidth={1.5} />
        </div>
        <h2
          className="mt-6 font-serif text-display-md font-medium tracking-tight text-balance animate-fade-up"
          style={{ animationDelay: "120ms" }}
        >
          {title}
        </h2>
        <p
          className="mt-2 text-base text-muted-foreground text-balance animate-fade-up"
          style={{ animationDelay: "190ms" }}
        >
          {subtitle}
        </p>
        <p
          className="mt-3 text-sm text-muted-foreground/80 text-balance animate-fade-up"
          style={{ animationDelay: "250ms" }}
        >
          {body}
        </p>
        <div
          className="mt-7 flex flex-wrap items-center justify-center gap-2 animate-fade-up"
          style={{ animationDelay: "310ms" }}
        >
          <Button variant="ai" size="lg" asChild className="glow-on-hover">
            <Link href={primaryHref} onClick={onContinue}>{primaryLabel}</Link>
          </Button>
          <Button variant="ghost" size="lg" onClick={onContinue}>
            {t("offers.celebrationContinue")}
          </Button>
        </div>
      </div>
    </div>
  );
}
