"use client";

/**
 * MatchRing — animated circular match-score indicator.
 *
 * SSR must carry the truth: the figure, the arc and the aria-label all render the
 * reader's real score on the very first paint. The sweep is a CSS keyframe (opens with
 * the arc at full gap, closes on the real offset), NOT a rAF counter — a paused or
 * occluded tab used to leave the dial at "0 %" forever even though the number lived
 * one frame away in React state.
 */
import * as React from "react";
import { cn } from "@/lib/utils";

const BAND_CLASS: Record<ScoreBand, string> = {
  strong: "text-success",
  good: "text-primary",
  fair: "text-warning",
  weak: "text-destructive",
};

export type ScoreBand = "strong" | "good" | "fair" | "weak";

export function scoreBand(v: number): ScoreBand {
  if (v >= 85) return "strong";
  if (v >= 70) return "good";
  if (v >= 50) return "fair";
  return "weak";
}

export interface MatchRingProps extends React.ComponentProps<"div"> {
  /** 0–100 */
  value: number;
  size?: number;
  thickness?: number;
  /** Screen-reader label, e.g. "Match" */
  label?: string;
  /** Show the percentage inside the ring */
  showValue?: boolean;
  /** Animate the sweep on mount (default true) */
  animated?: boolean;
}

function MatchRing({
  value,
  size = 72,
  thickness = 6,
  label = "Match",
  showValue = true,
  animated = true,
  className,
  ...props
}: MatchRingProps) {
  const clamped = Math.max(0, Math.min(100, value));
  const radius = (size - thickness) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - clamped / 100);

  const band = BAND_CLASS[scoreBand(clamped)];

  return (
    <div
      role="img"
      aria-label={`${label}: ${clamped}%`}
      className={cn("relative inline-flex shrink-0 items-center justify-center", band, className)}
      style={{ width: size, height: size }}
      {...props}
    >
      <svg width={size} height={size} className="-rotate-90" aria-hidden>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeOpacity={0.14}
          strokeWidth={thickness}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth={thickness}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          style={{
            ["--ring-from" as string]: `${circumference}`,
            ["--ring-to" as string]: `${offset}`,
            animation: animated
              ? "scoreRingDraw 900ms cubic-bezier(0.16, 1, 0.3, 1) both"
              : undefined,
          }}
        />
      </svg>
      {showValue && (
        <span className="absolute inset-0 flex items-center justify-center text-sm font-semibold tabular-nums text-foreground">
          {Math.round(clamped)}
          <span className="text-2xs font-normal text-muted-foreground">%</span>
        </span>
      )}
    </div>
  );
}

export { MatchRing };
