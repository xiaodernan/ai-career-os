"use client";

import * as React from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { pageWindow } from "@/lib/page-window";
import { useLocale } from "@/lib/i18n/locale-context";
import { Button } from "@/components/ui/button";

/**
 * Pager — server-side page/size navigation with an honest row count.
 *
 * The window comes from `pageWindow`, which clamps an out-of-range page to the last page
 * that exists. A URL the set has shrunk past (`?page=5` over 35 rows) used to print
 * "101–30 of 35" -- `from` read the URL's page, `to` the total -- for the frame before the
 * screen's own correction effect ran, and forever on a screen without one. The pager now
 * says what the last real page holds, and Prev/Next step from there.
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
  const view = pageWindow(page, size, total);
  const { t } = useLocale();

  return (
    <nav
      aria-label={t("chrome.pagination", { label })}
      className={cn("flex items-center justify-between gap-3", className)}
    >
      <p className="text-xs text-muted-foreground" aria-live="polite">
        {total > 0 ? (
          t("chrome.ofTotal", {
            from: view.from,
            to: view.to,
            total,
            label,
          })
        ) : (
          t("chrome.noRowsYet", { label })
        )}
      </p>
      <div className="flex items-center gap-1.5">
        <Button
          variant="outline"
          size="sm"
          disabled={view.page <= 0}
          onClick={() => onPageChange(view.page - 1)}
          aria-label={t("chrome.previousPage")}
        >
          <ChevronLeft aria-hidden />
          {t("chrome.prev")}
        </Button>
        <span className="px-1 text-xs text-muted-foreground tabular-nums">
          {view.page + 1} / {view.pageCount}
        </span>
        <Button
          variant="outline"
          size="sm"
          disabled={view.page + 1 >= view.pageCount}
          onClick={() => onPageChange(view.page + 1)}
          aria-label={t("chrome.nextPage")}
        >
          {t("chrome.next")}
          <ChevronRight aria-hidden />
        </Button>
      </div>
    </nav>
  );
}
