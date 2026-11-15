"use client";

import * as React from "react";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";

/**
 * A single, reusable hint for icon-only and dense controls on the main
 * screens: a visible hover tip instead of making the reader guess what a
 * glyph does. Nothing here calls the model; the hint is the reader's
 * manual stapled to the button.
 */
export function Hint({
  label,
  side = "bottom",
  children,
}: {
  label: string;
  side?: "top" | "bottom" | "left" | "right";
  children: React.ReactNode;
}) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>{children}</TooltipTrigger>
      <TooltipContent side={side}>{label}</TooltipContent>
    </Tooltip>
  );
}
