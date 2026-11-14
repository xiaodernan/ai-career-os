"use client";

import * as React from "react";
import { Check } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * EmptyComposition — the designed emptiness, composed, not default.
 *
 * An empty screen is a promise the page makes before it has anything to
 * show. This composition is that promise taken seriously: a buoyant icon in a
 * ringed, glowing disc; one eyebrow that names the payoff in the reader's
 * language (the promise line); the sentence that says how (title) plus the one
 * short paragraph that says why (description); the single action that starts
 * it; and up to three proof points the product can actually stand behind. Every
 * proof is written from what the codebase ships today, never from aspirations;
 * a surface that cannot defend three proofs should pass two, not invent one.
 *
 * Every animation is opacity/transform only — the compositor owns the work.
 * The stagger (80/140/200/260/320ms) is the mount itself; no timers, no
 * content ever hidden from markup. `prefers-reduced-motion` collapses both to
 * instant via the blanket rule in globals.css.
 */
export interface EmptyCompositionProps extends React.ComponentProps<"div"> {
  icon?: React.ReactNode;
  /** The payoff sentence in the reader's language — what shows up here once it does its job. */
  promise?: string;
  title: string;
  description?: string;
  action?: React.ReactNode;
  /** Up to three proofs, each one defensible from shipped behavior. */
  proofs?: string[];
}

export function EmptyComposition({
  icon,
  promise,
  title,
  description,
  action,
  proofs,
  className,
  ...props
}: EmptyCompositionProps) {
  const proofList = (proofs ?? []).slice(0, 3);
  return (
    <div
      className={cn(
        "relative flex flex-col items-center justify-center gap-1.5 overflow-hidden px-6 py-10 text-center",
        className
      )}
      {...props}
    >
      {/* Atmosphere: one glow, one hairline. Nothing moves; nothing competes with the CTA. */}
      <div aria-hidden className="pointer-events-none absolute size-44 rounded-full bg-primary/[0.08] blur-3xl" />
      <div
        aria-hidden
        className="pointer-events-none absolute h-px w-48 -translate-y-[70px] bg-gradient-to-r from-transparent via-primary/50 to-transparent"
      />

      <div className="relative flex size-14 items-center justify-center rounded-2xl border border-primary/25 bg-primary/[0.06] text-primary shadow-[0_0_36px_-8px_color-mix(in_oklch,var(--primary)_38%,transparent)] [&_svg]:size-6 animate-scale-in">
        {icon}
      </div>

      {promise ? (
        <p
          className="relative mt-1 text-2xs font-semibold tracking-[0.18em] text-primary/80 uppercase animate-fade-up"
          style={{ animationDelay: "70ms" }}
        >
          {promise}
        </p>
      ) : null}

      <h3
        className="relative text-base font-semibold text-foreground animate-fade-up"
        style={{ animationDelay: "130ms" }}
      >
        {title}
      </h3>

      {description ? (
        <p
          className="relative max-w-md text-sm leading-relaxed text-muted-foreground animate-fade-up"
          style={{ animationDelay: "190ms" }}
        >
          {description}
        </p>
      ) : null}

      {action ? (
        <div
          className="relative mt-2.5 flex flex-wrap items-center justify-center gap-2 animate-fade-up"
          style={{ animationDelay: "250ms" }}
        >
          {action}
        </div>
      ) : null}

      {proofList.length ? (
        <ul
          className="relative mt-4 flex flex-col gap-1.5 border-t border-border/60 pt-4 text-left animate-fade-up sm:flex-row sm:gap-6"
          style={{ animationDelay: "310ms" }}
        >
          {proofList.map((p) => (
            <li key={p} className="flex items-start gap-1.5 text-xs leading-snug text-muted-foreground">
              <Check className="mt-0.5 size-3.5 shrink-0 text-success" aria-hidden />
              <span>{p}</span>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
