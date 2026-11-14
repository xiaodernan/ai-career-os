import * as React from "react";
import { cn } from "@/lib/utils";

/**
 * PageGrid — the 12-column content contract every signed-in route shares.
 *
 * Width scale: `form` (832px) for data-entry pages, `content` (1152px) for
 * lists and detail views, `board` (1408px) for wide boards. Children that are
 * not a <GridSpan> span all twelve columns at every breakpoint (`[&>*]:col-span-12`),
 * so a bare route looks exactly like it does today; a child opts into a narrower
 * span with <GridSpan span={7}>, full width on mobile, 7 columns at md and up.
 */

export const PAGE_WIDTHS = {
  form: "max-w-3xl",
  content: "max-w-6xl",
  board: "max-w-[88rem]",
} as const;

export type PageWidth = keyof typeof PAGE_WIDTHS;

const SPAN: Record<number, string> = {
  1: "md:col-span-1",
  2: "md:col-span-2",
  3: "md:col-span-3",
  4: "md:col-span-4",
  5: "md:col-span-5",
  6: "md:col-span-6",
  7: "md:col-span-7",
  8: "md:col-span-8",
  9: "md:col-span-9",
  10: "md:col-span-10",
  11: "md:col-span-11",
  12: "md:col-span-12",
};

export type PageGridProps = React.ComponentProps<"div">;

export function PageGrid({ className, ...props }: PageGridProps) {
  return (
    <div
      className={cn("grid w-full grid-cols-12 gap-4 [&>*]:col-span-12", className)}
      {...props}
    />
  );
}

export interface GridSpanProps extends React.ComponentProps<"div"> {
  /** Columns at md and up. Clamped to 1..12; 12 renders exactly like a bare child. */
  span?: number;
}

export function GridSpan({ span = 12, className, ...props }: GridSpanProps) {
  const n = Math.min(12, Math.max(1, Math.round(span)));
  return <div className={cn("col-span-12", SPAN[n], className)} {...props} />;
}
