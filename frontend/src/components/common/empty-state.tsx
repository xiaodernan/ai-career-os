import * as React from "react";
import { cn } from "@/lib/utils";
import { EmptyComposition } from "./empty-composition";

/**
 * EmptyState — designed emptiness per the UX contract (§7): never a bare
 * "no data". Illustration slot, title, description, action — plus, when the
 * surface passes them, the composed promise above the title and the proof
 * list beneath the CTA (Epic 3: the empty becomes the product's salesman).
 */
export interface EmptyStateProps extends React.ComponentProps<"div"> {
  icon?: React.ReactNode;
  /** Optional slot replacing the icon circle (drop a small SVG illustration there) */
  illustration?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
  /** The payoff sentence rendered as an eyebrow above the title (Epic 3). */
  promise?: string;
  /** Up to three proof points, in the reader's language (Epic 3). */
  proofs?: string[];
}

function EmptyState({
  icon,
  illustration,
  title,
  description,
  action,
  promise,
  proofs,
  className,
  ...props
}: EmptyStateProps) {
  if (promise || (proofs && proofs.length > 0)) {
    return (
      <EmptyComposition
        icon={illustration ?? icon}
        promise={promise}
        title={title}
        description={description}
        action={action}
        proofs={proofs}
        className={className}
        {...props}
      />
    );
  }
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
