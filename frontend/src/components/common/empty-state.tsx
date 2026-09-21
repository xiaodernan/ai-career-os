import * as React from "react";
import { cn } from "@/lib/utils";

/**
 * EmptyState — designed emptiness per the UX contract (§7): never a bare
 * "no data". Illustration slot, title, description, action.
 */
export interface EmptyStateProps extends React.ComponentProps<"div"> {
  icon?: React.ReactNode;
  /** Optional slot replacing the icon circle (drop a small SVG illustration there) */
  illustration?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
}

function EmptyState({
  icon,
  illustration,
  title,
  description,
  action,
  className,
  ...props
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-1 px-6 py-10 text-center",
        className
      )}
      {...props}
    >
      {illustration ?? (
        <div className="mb-2 flex size-11 items-center justify-center rounded-xl border border-border/70 bg-muted text-muted-foreground shadow-soft [&_svg]:size-5">
          {icon}
        </div>
      )}
      <h3 className="text-sm font-semibold text-foreground">{title}</h3>
      {description && (
        <p className="max-w-sm text-sm text-muted-foreground">{description}</p>
      )}
      {action && <div className="mt-3 flex items-center gap-2">{action}</div>}
    </div>
  );
}

export { EmptyState };
