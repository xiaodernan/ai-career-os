"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

/**
 * A minimal horizontal bar chart.
 *
 * The product has no chart library, and adding one for three screens of bars
 * would be a dependency the bundle pays for on every page. So this is the whole
 * chart: an SVG per row, a scale the caller owns, and the numbers printed beside
 * it — because a bar nobody can read the value of is a picture, not a chart.
 *
 * Two things are deliberate:
 *
 * - **The scale is the caller's.** A funnel's stages and a latency histogram
 *   do not share a maximum, and a chart that picks one for them is a chart that
 *   lies about the smaller one. The caller passes `max`, or the component takes
 *   the largest value it was given.
 * - **The value is always visible.** The bar is the shape; the number is the
 *   fact. A screen reader gets the number, and a reader who cannot see the
 *   colour still reads the value.
 */

export interface BarDatum {
  /** The row's own label — the stage name, the agent's name. */
  label: string;
  /** The value the bar measures. */
  value: number;
  /** A shorter line under the label: the count, the share, the unit. */
  detail?: string;
  /** A tone for the bar; the default is the primary accent. */
  tone?: "primary" | "success" | "warning" | "destructive" | "muted";
}

const TONE_CLASS: Record<NonNullable<BarDatum["tone"]>, string> = {
  primary: "bg-primary",
  success: "bg-success",
  warning: "bg-warning",
  destructive: "bg-destructive",
  muted: "bg-muted-foreground/50",
};

export function BarChart({
  data,
  max,
  className,
  emptyHint = "Nothing to plot yet.",
  valueFormat,
}: {
  data: BarDatum[];
  /** The scale's top. Defaults to the largest value in the data. */
  max?: number;
  className?: string;
  /** What to say when there is no data. */
  emptyHint?: string;
  /** How to print the value. Defaults to a plain number. */
  valueFormat?: (value: number) => string;
}) {
  if (!data.length) {
    return <p className="text-sm text-muted-foreground">{emptyHint}</p>;
  }

  // The scale is the caller's, or the largest value: a bar that always fills
  // the width would make a 1-of-100 and a 50-of-100 look the same.
  const top = max ?? Math.max(...data.map((d) => d.value), 1);
  const format = valueFormat ?? ((v: number) => String(v));

  return (
    <ul className={cn("space-y-2.5", className)}>
      {data.map((row) => {
        // A negative value is not a bar; a zero is an empty one. Both render
        // the number and neither renders a negative width.
        const ratio = row.value > 0 ? Math.min(1, row.value / top) : 0;
        return (
          <li key={row.label} className="space-y-1">
            <div className="flex items-baseline justify-between gap-3">
              <span className="truncate text-sm font-medium">{row.label}</span>
              <span className="shrink-0 text-sm tabular-nums text-muted-foreground">
                {format(row.value)}
              </span>
            </div>
            <div
              className="h-2 overflow-hidden rounded-full bg-muted"
              role="img"
              aria-label={`${row.label}: ${format(row.value)}`}
            >
              <div
                className={cn("h-full rounded-full transition-[width] duration-300", TONE_CLASS[row.tone ?? "primary"])}
                style={{ width: `${ratio * 100}%` }}
              />
            </div>
            {row.detail && (
              <p className="text-xs text-muted-foreground">{row.detail}</p>
            )}
          </li>
        );
      })}
    </ul>
  );
}

/**
 * A share row: a labelled segment of a whole, with the numbers beside it.
 *
 * The funnel's conversion is a share of the applications that were submitted,
 * and the share is the fact — so it is printed, not only drawn.
 */
export function ShareChart({
  data,
  className,
  emptyHint = "Nothing to plot yet.",
}: {
  data: BarDatum[];
  className?: string;
  emptyHint?: string;
}) {
  if (!data.length) {
    return <p className="text-sm text-muted-foreground">{emptyHint}</p>;
  }
  const total = data.reduce((sum, d) => sum + Math.max(0, d.value), 0);
  return (
    <div className={cn("space-y-2", className)}>
      <div
        className="flex h-3 overflow-hidden rounded-full bg-muted"
        role="img"
        aria-label={data.map((d) => `${d.label}: ${d.value}`).join(", ")}
      >
        {data.map((d) => {
          const share = total > 0 ? Math.max(0, d.value) / total : 0;
          if (share <= 0) return null;
          return (
            <div
              key={d.label}
              className={cn("h-full", TONE_CLASS[d.tone ?? "primary"])}
              style={{ width: `${share * 100}%` }}
            />
          );
        })}
      </div>
      <ul className="space-y-1">
        {data.map((d) => (
          <li key={d.label} className="flex items-center justify-between gap-3 text-sm">
            <span className="flex min-w-0 items-center gap-2">
              <span
                className={cn("size-2 shrink-0 rounded-full", TONE_CLASS[d.tone ?? "primary"])}
                aria-hidden
              />
              <span className="truncate">{d.label}</span>
            </span>
            <span className="shrink-0 tabular-nums text-muted-foreground">
              {d.detail ?? d.value}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
