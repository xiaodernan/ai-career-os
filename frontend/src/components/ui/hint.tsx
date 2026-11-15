"use client";

import * as React from "react";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";

/**
 * A single, reusable hint for icon-only and dense controls on the main
 * screens: a visible hover tip instead of making the reader guess what a
 * glyph does. Nothing here calls the model; the hint is the reader's
 * manual stapled to the button.
 *
 * Carries its own provider on purpose: the app-shell provider at `(app)/layout.tsx`
 * covers every signed-in route, but storybook-style renders, unit tests, and
 * a future public surface that wants a hint outside the shell all render
 * `<Hint>` without one, and a silent missing-provider crash is worse than
 * one redundant provider.
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
    <TooltipProvider delayDuration={200}>
      <Tooltip>
        <TooltipTrigger asChild>{children}</TooltipTrigger>
        <TooltipContent side={side}>{label}</TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
