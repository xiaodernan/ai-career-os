"use client";

import * as React from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

/**
 * Pager — server-side page/size navigation with an honest row count.
 */
export function Pagination({
  page,
  size,
  total,
  onPageChange,
  className,
  label = "results",
}: {
  page: number;
  size: number;
  total: number;
  onPageChange: (page: number) => void;
  className?: string;
  label?: string;
}) {
  const pageCount = size > 0 ? Math.max(1, Math.ceil(total / size)) : 1;
  const from = total === 0 ? 0 : page * size + 1;
  const to = Math.min(total, (page + 1) * size);

  return (
    <nav
      aria-label={`Pagination (${label})`}
      className={cn("flex items-center justify-between gap-3", className)}
    >
      <p className="text-xs text-muted-foreground" aria-live="polite">
        {total > 0 ? (
          <>
            <span className="font-medium text-foreground tabular-nums">
              {from}–{to}
            </span>{" "}
            of <span className="tabular-nums">{total}</span> {label}
          </>
        ) : (
          <>No {label} yet</>
        )}
      </p>
      <div className="flex items-center gap-1.5">
        <Button
          variant="outline"
          size="sm"
          disabled={page <= 0}
          onClick={() => onPageChange(page - 1)}
          aria-label="Previous page"
        >
          <ChevronLeft aria-hidden />
          Prev
        </Button>
        <span className="px-1 text-xs text-muted-foreground tabular-nums">
          {page + 1} / {pageCount}
        </span>
        <Button
          variant="outline"
          size="sm"
          disabled={page + 1 >= pageCount}
          onClick={() => onPageChange(page + 1)}
          aria-label="Next page"
        >
          Next
          <ChevronRight aria-hidden />
        </Button>
      </div>
    </nav>
  );
}
