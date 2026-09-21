"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

/**
 * MatchRing — animated circular match-score indicator.
 * Color follows the score band; sweep-in on mount via stroke-dashoffset transition.
 */
export type ScoreBand = "strong" | "good" | "fair" | "weak";

export function scoreBand(value: number): ScoreBand {
  if (value >= 80) return "strong";
  if (value >= 60) return "good";
  if (value >= 40) return "fair";
  return "weak";
}

const BAND_CLASS: Record<ScoreBand, string> = {
  strong: "text-success",
  good: "text-primary",
  fair: "text-warning",
  weak: "text-destructive",
};

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
  const [progress, setProgress] = React.useState(animated ? 0 : clamped);

  React.useEffect(() => {
    if (!animated) {
      setProgress(clamped);
      return;
    }
    const raf = requestAnimationFrame(() => setProgress(clamped));
    return () => cancelAnimationFrame(raf);
  }, [clamped, animated]);

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
          strokeDashoffset={circumference * (1 - progress / 100)}
          style={{
            transition: animated
              ? "stroke-dashoffset 900ms cubic-bezier(0.16,1,0.3,1)"
              : undefined,
          }}
        />
      </svg>
      {showValue && (
        <span className="absolute inset-0 flex items-center justify-center text-sm font-semibold tabular-nums text-foreground">
          {Math.round(progress)}
          <span className="text-2xs font-normal text-muted-foreground">%</span>
        </span>
      )}
    </div>
  );
}

export { MatchRing };
