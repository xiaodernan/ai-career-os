"use client";

import * as React from "react";
import { ArrowDownRight, ArrowUpRight, Minus } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

/**
 * One KPI tile — the shape the monitoring, analysis and dashboard pages draw side
 * by side: a glyph chip + label above a large tabular number, with `warning`
 * lighting the value in the deck's warning color when the number needs the
 * reader's eye.
 *
 * The polish is deliberately cheap where it is seen and honest where it is not:
 * the value renders at its final figure on the server and in tests (a KPI that
 * flashes "0" before its script runs is a lie to the reader and to no-JS mode),
 * then — only when motion is allowed — counts up from zero over ~700ms with an
 * ease-out curve. The trend chip is a real sentence for the screen reader, not a
 * bare triangle. Hover lifts the tile and brightens the accent hairline; both are
 * CSS, so nothing moves unless the pointer says so.
 */

export interface MetricDelta {
  /** The delta the number carries, already formatted ("+12", "-3%"). */
  label: string;
  direction: "up" | "down" | "flat";
  /** Whether "up" is good (green) or bad (red) for this metric. */
  goodWhenUp?: boolean;
}

function CountUp({ value }: { value: string }) {
  // Count up only the numeric leading part of the rendered string ("1,234" /
  // "5.2"), keeping any suffix ("ms", "%") glued to it. Non-numeric values
  // ("—", "Healthy") render exactly as given, and the server's first paint is
  // always the final figure: the animation is an enhancement, never the truth.
  const match = value.match(/^([0-9][0-9,]*(?:\.[0-9]+)?)(.*)$/);
  const [shown, setShown] = React.useState<string>(value);

  React.useEffect(() => {
    if (!match) return;
    const end = Number(match[1].replace(/,/g, ""));
    if (!Number.isFinite(end) || end === 0) return;
    if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) return;
    const suffix = match[2];
    const decimals = match[1].includes(".") ? match[1].split(".")[1].length : 0;
    const startedAt = performance.now();
    const durationMs = 700;
    let raf = 0;
    const tick = (now: number) => {
      const t = Math.min(1, (now - startedAt) / durationMs);
      const eased = 1 - Math.pow(1 - t, 3);
      setShown(
        (end * eased).toLocaleString(undefined, {
          minimumFractionDigits: decimals,
          maximumFractionDigits: decimals,
        }) + suffix,
      );
      if (t < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
    // Re-run only when the underlying figure changes: the parts are derived from it.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);

  if (!match) return <>{value}</>;
  return <>{shown}</>;
}

export function MetricCard({
  icon,
  label,
  value,
  tone,
  hint,
  delta,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  tone?: "warning";
  hint?: string;
  delta?: MetricDelta;
}) {
  const deltaColor =
    delta?.direction === "flat"
      ? "text-muted-foreground"
      : (delta?.direction === "up") === (delta?.goodWhenUp !== false)
        ? "text-success"
        : "text-destructive";
  const DeltaGlyph =
    delta?.direction === "up" ? ArrowUpRight
      : delta?.direction === "down" ? ArrowDownRight : Minus;

  return (
    <Card
      className={cn(
        "group relative overflow-hidden transition-all duration-200",
        "hover:-translate-y-0.5 hover:shadow-lg hover:shadow-primary/10",
      )}
    >
      {/* The accent hairline: a flat border line that becomes a gradient as the pointer arrives. */}
      <span
        aria-hidden
        className="absolute inset-x-0 top-0 h-0.5 bg-border transition-colors duration-200 group-hover:bg-gradient-to-r group-hover:from-primary/70 group-hover:via-primary/30 group-hover:to-transparent"
      />
      <CardHeader className="gap-2">
        <CardDescription className="flex items-center gap-2">
          <span
            aria-hidden
            className="flex size-7 items-center justify-center rounded-lg border border-border/60 bg-muted/50 text-muted-foreground transition-colors duration-200 group-hover:border-primary/30 group-hover:text-foreground [&_svg]:size-3.5"
          >
            {icon}
          </span>
          {label}
        </CardDescription>
        <CardTitle
          className={cn(
            "flex items-baseline gap-2 text-2xl font-semibold tabular-nums",
            tone === "warning" && "text-warning",
          )}
        >
          <CountUp value={value} />
          {delta && (
            <span
              className={cn(
                "flex items-center gap-0.5 rounded-full border border-border/60 bg-muted/40 px-1.5 py-0.5 text-2xs font-medium tabular-nums",
                deltaColor,
              )}
            >
              <DeltaGlyph aria-hidden className="size-3" />
              <span>{delta.label}</span>
              <span className="sr-only">
                {delta.direction === "up"
                  ? ", rising"
                  : delta.direction === "down"
                    ? ", falling"
                    : ", unchanged"}
              </span>
            </span>
          )}
        </CardTitle>
      </CardHeader>
      {hint && <CardContent className="text-xs text-muted-foreground">{hint}</CardContent>}
    </Card>
  );
}
