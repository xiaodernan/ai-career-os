"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

/**
 * SourceChip — inline citation marker [1] used inside streaming text blocks.
 * Hover/focus reveals the source document title.
 */
export interface SourceChipProps
  extends Omit<React.ComponentProps<"button">, "children"> {
  index: number;
  docTitle: string;
  section?: string;
}

function SourceChip({ index, docTitle, section, className, ...props }: SourceChipProps) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <button
          type="button"
          aria-label={`Citation ${index}: ${docTitle}${section ? ` — ${section}` : ""}`}
          className={cn(
            "mx-0.5 -mt-2 inline-flex h-fit items-center rounded-md border border-primary/25 bg-primary/10 px-1 align-top font-mono text-2xs leading-4 font-medium text-primary transition-colors duration-150 hover:bg-primary/20 focus-visible:ring-[3px] focus-visible:ring-primary/30 focus-visible:outline-none",
            className
          )}
          {...props}
        >
          {index}
        </button>
      </TooltipTrigger>
      <TooltipContent side="top" className="max-w-60">
        <span className="font-medium">{docTitle}</span>
        {section && <span className="text-muted-foreground"> · {section}</span>}
      </TooltipContent>
    </Tooltip>
  );
}

export { SourceChip };
