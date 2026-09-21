"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { EvidenceCard } from "@/components/ai/evidence-card";
import { Badge } from "@/components/ui/badge";
import { evidencePath } from "@/lib/api/normalize";
import type { Evidence } from "@/lib/api/types";

/**
 * EvidenceList — the RAG explainability surface (§6): every AI conclusion is
 * shown next to the quote it came from and the document/section breadcrumb.
 * Renders nothing when there is no evidence; never renders a stub quote.
 */
export interface EvidenceListProps extends React.ComponentProps<"ul"> {
  items: Evidence[];
  /** Cap the visible count (the rest collapse behind a "show all" button). */
  limit?: number;
  /** In-app href resolver, e.g. map a docId to the knowledge source page. */
  hrefFor?: (e: Evidence) => string | undefined;
  dense?: boolean;
}

function EvidenceList({ items, limit, hrefFor, dense = false, className, ...props }: EvidenceListProps) {
  const [expanded, setExpanded] = React.useState(false);
  const visible = limit && !expanded ? items.slice(0, limit) : items;
  if (!items.length) return null;

  return (
    <ul className={cn("flex flex-col gap-2", className)} {...props}>
      {visible.map((e, i) => (
        <li key={`${e.criterion}-${i}`}>
          <EvidenceCard
            quote={e.quote}
            sourcePath={evidencePath(e)}
            docTitle={e.source?.docTitle}
            href={hrefFor?.(e) ?? e.href}
            className={cn(dense && "p-2.5 text-xs")}
            accessory={
              e.score != null ? (
                <Badge variant="outline" className="tabular-nums">
                  {Math.round(e.score)}
                  <span className="text-muted-foreground">/100</span>
                </Badge>
              ) : e.source?.kind ? (
                <Badge variant="outline" className="capitalize">
                  {e.source.kind.replace(/_/g, " ")}
                </Badge>
              ) : null
            }
          >
            <figcaption className="mt-1.5 text-xs text-muted-foreground">
              <span className="font-medium text-foreground">{e.criterion}</span>
              {e.reasoning && <> · {e.reasoning}</>}
            </figcaption>
          </EvidenceCard>
        </li>
      ))}
      {limit && items.length > limit && (
        <li>
          <button
            type="button"
            onClick={() => setExpanded((v) => !v)}
            className="rounded-md px-1 text-xs font-medium text-primary underline-offset-4 hover:underline focus-visible:ring-[3px] focus-visible:ring-primary/30"
          >
            {expanded ? "Show fewer" : `Show all ${items.length} evidence items`}
          </button>
        </li>
      )}
    </ul>
  );
}

export { EvidenceList };
