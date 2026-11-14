import * as React from "react";
import { cn } from "@/lib/utils";
import { PageHeader, type PageHeaderProps } from "@/components/common/page-header";
import { GridSpan, PageGrid, PAGE_WIDTHS, type PageWidth } from "@/components/layout/page-grid";

/**
 * PageShell — the one layout contract for signed-in routes.
 *
 * A width from the scale, the same heading block every page gets (PageHeader,
 * optional `frontDoor` band when the call site asks out loud), and a 12-column
 * content grid below it. Bare children span all twelve columns, matching today;
 * a child that wants a narrower column wraps itself in <GridSpan>. The contract
 * does not invent data or fetch anything — it is the page's *frame*, nothing more.
 *
 * `RouteGlance` is deliberately not part of this shell: its "what this page
 * measured this visit" chip is meaningful only when wired to real per-route
 * measurements, not as decoration — it ships when its source measurement exists.
 */
export interface PageShellProps extends Omit<PageHeaderProps, "className" | "children"> {
  /** Width scale. `content` is the default (1152px) — the Linear/Notion reading measure. */
  width?: PageWidth;
  className?: string;
  gridClassName?: string;
  children: React.ReactNode;
}

export function PageShell({
  width = "content",
  className,
  gridClassName,
  children,
  ...header
}: PageShellProps) {
  return (
    <div className={cn("mx-auto flex w-full flex-col gap-6", PAGE_WIDTHS[width], className)}>
      <PageHeader {...header} />
      <PageGrid className={gridClassName}>{children}</PageGrid>
    </div>
  );
}

export { GridSpan, PageGrid, PAGE_WIDTHS };
export type { PageWidth };
