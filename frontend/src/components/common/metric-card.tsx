"use client";

import * as React from "react";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

/**
 * One KPI tile — the shape the monitoring and analysis pages draw side by side:
 * a muted glyph + label above a large tabular number, with `warning` lighting the
 * value in the deck's warning color when the number needs the reader's eye.
 *
 * Both pages had their own byte-for-byte copy of this before Epic 177's follow-up;
 * one implementation means one place where a tone, a type or a spacing changes.
 */
export function MetricCard({
  icon,
  label,
  value,
  tone,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  tone?: "warning";
}) {
  return (
    <Card>
      <CardHeader>
        <CardDescription className="flex items-center gap-1.5">
          <span className="text-muted-foreground [&_svg]:size-3.5">{icon}</span>
          {label}
        </CardDescription>
        <CardTitle
          className={`text-2xl font-semibold tabular-nums ${tone === "warning" ? "text-warning" : ""}`}
        >
          {value}
        </CardTitle>
      </CardHeader>
    </Card>
  );
}
