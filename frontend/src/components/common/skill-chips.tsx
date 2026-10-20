"use client";

import * as React from "react";
import { Check, Circle } from "lucide-react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { scoreBand } from "@/components/ai/match-ring";
import { useLocale } from "@/lib/i18n/locale-context";

/**
 * SkillChips — the PRD's job-card language: matched skills carry a check,
 * missing skills an open circle. Colour follows the AI visual language only
 * (success / muted), never a gradient.
 */
export interface SkillChipsProps extends React.ComponentProps<"ul"> {
  matched?: string[];
  missing?: string[];
  max?: number;
  /** "why this job" eyebrow above the matched row */
  showLabels?: boolean;
}

function SkillChips({
  matched = [],
  missing = [],
  max = 6,
  showLabels = false,
  className,
  ...props
}: SkillChipsProps) {
  const { t } = useLocale();
  const shownMatched = matched.slice(0, max);
  const shownMissing = missing.slice(0, max);
  if (!matched.length && !missing.length) return null;

  return (
    <ul className={cn("flex flex-wrap items-center gap-1.5", className)} {...props}>
      {showLabels && matched.length > 0 && (
        <li className="text-2xs font-medium tracking-wide text-muted-foreground uppercase">
          {t("skillChips.why")}
        </li>
      )}
      {shownMatched.map((s) => (
        <li key={`m-${s}`}>
          <Badge variant="success" className="gap-1 font-normal">
            <Check className="size-3" strokeWidth={2.5} aria-hidden />
            {s}
          </Badge>
        </li>
      ))}
      {matched.length > shownMatched.length && (
        <li className="text-2xs text-muted-foreground">+{matched.length - shownMatched.length}</li>
      )}
      {showLabels && missing.length > 0 && (
        <li className="ml-1 text-2xs font-medium tracking-wide text-muted-foreground uppercase">
          {t("skillChips.missing")}
        </li>
      )}
      {shownMissing.map((s) => (
        <li key={`x-${s}`}>
          <Badge variant="outline" className="gap-1 border-border/80 font-normal text-muted-foreground">
            <Circle className="size-2.5" aria-hidden />
            {s}
          </Badge>
        </li>
      ))}
      {missing.length > shownMissing.length && (
        <li className="text-2xs text-muted-foreground">+{missing.length - shownMissing.length}</li>
      )}
    </ul>
  );
}

export { SkillChips };

/** Single neutral skill pill (filters, JD requirements). */
export function SkillPill({
  children,
  active,
  className,
  ...props
}: React.ComponentProps<"span"> & { active?: boolean }) {
  return (
    <Badge
      variant={active ? "ai" : "outline"}
      className={cn("text-2xs font-normal", className)}
      {...props}
    >
      {children}
    </Badge>
  );
}

/* ------------------------------------------------------------------ */
/* DimensionBars — per-dimension score breakdown (match + interview)   */
/* ------------------------------------------------------------------ */

export interface DimensionBar {
  key: string;
  label: string;
  score?: number;
  note?: string;
}

export interface DimensionBarsProps extends React.ComponentProps<"ul"> {
  dimensions: DimensionBar[];
  /** Compact rows for card bodies */
  dense?: boolean;
}

function DimensionBars({ dimensions, dense = false, className, ...props }: DimensionBarsProps) {
  if (!dimensions.length) return null;
  return (
    <ul className={cn("flex flex-col gap-2.5", className)} {...props}>
      {dimensions.map((d) => {
        const value = Math.max(0, Math.min(100, d.score ?? 0));
        const band = scoreBand(value);
        return (
          <li key={d.key} className="grid gap-1">
            <div className="flex items-baseline justify-between gap-3">
              <span className={cn("truncate text-muted-foreground", dense ? "text-xs" : "text-sm")}>
                {d.label}
              </span>
              <span
                className={cn(
                  "shrink-0 font-medium tabular-nums",
                  band === "strong" && "text-success",
                  band === "good" && "text-primary",
                  band === "fair" && "text-warning",
                  band === "weak" && "text-destructive",
                  dense ? "text-xs" : "text-sm"
                )}
              >
                {d.score == null ? "—" : `${Math.round(value)}`}
                <span className="text-2xs text-muted-foreground">%</span>
              </span>
            </div>
            <div
              role="meter"
              aria-valuenow={Math.round(value)}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label={d.label}
              className={cn("w-full overflow-hidden rounded-full bg-muted", dense ? "h-1" : "h-1.5")}
            >
              <div
                className={cn(
                  "h-full rounded-full transition-[width] duration-700 ease-[cubic-bezier(0.16,1,0.3,1)] motion-reduce:transition-none",
                  band === "strong" && "bg-success",
                  band === "good" && "bg-primary",
                  band === "fair" && "bg-warning",
                  band === "weak" && "bg-destructive"
                )}
                style={{ width: `${value}%` }}
              />
            </div>
            {d.note && !dense && (
              <p className="text-xs text-muted-foreground">{d.note}</p>
            )}
          </li>
        );
      })}
    </ul>
  );
}

export { DimensionBars };
