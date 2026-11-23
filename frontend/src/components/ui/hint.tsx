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
 *
 * `anchor` says which element the tip attaches to, and it matters because Radix
 * `Slot` gives the caller's props precedence over the child's, and every Radix
 * primitive writes its own state into the one attribute `data-state`. Measured in
 * a browser on the jobs board: `<Hint>` around a `TabsTrigger` left the selected
 * tab reporting `aria-selected="true"` beside `data-state="closed"` -- the
 * tooltip's value, not the tab's -- and `tabs.tsx` styles the active tab and its
 * underline from that attribute. `anchor="span"` binds the tip to a boxless
 * wrapper instead so the control keeps its own state; hover and focus reach the
 * wrapper as they bubble out of the control, so the tip still opens from the
 * keyboard.
 */
export function Hint({
  label,
  side = "bottom",
  anchor = "child",
  children,
}: {
  label: string;
  side?: "top" | "bottom" | "left" | "right";
  anchor?: "child" | "span";
  children: React.ReactNode;
}) {
  return (
    <TooltipProvider delayDuration={200}>
      <Tooltip>
        {anchor === "span" ? (
          <TooltipTrigger asChild>
            <span className="contents">{children}</span>
          </TooltipTrigger>
        ) : (
          <TooltipTrigger asChild>{children}</TooltipTrigger>
        )}
        <TooltipContent side={side}>{label}</TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
