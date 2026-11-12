import * as React from "react";
import { cn } from "@/lib/utils";

/**
 * PageHeader — consistent page title block with description + actions row.
 *
 * `frontDoor` opts the header into the designed "front door" band: static
 * light-theme ambient washes, a dark-only aurora (screen-blend over a light
 * card would wash it white — the jobs/dashboard trap), a shimmer hairline at
 * the top edge, and a CSS-only staggered entrance. It adds zero client JS,
 * zero routes, zero copy; the motion layers are decorative and inert. Off by
 * default so the bespoke shells (dashboard/jobs/resumes/interviews/notifications)
 * keep ownership of the band they pin in their own contracts — and a call site
 * must ask for it out loud, never inherit it silently.
 */
export interface PageHeaderProps extends Omit<React.ComponentProps<"div">, "title"> {
  title: React.ReactNode;
  description?: React.ReactNode;
  actions?: React.ReactNode;
  /** Render the band. Default: the plain block, byte-for-byte the old shape. */
  frontDoor?: boolean;
}

function PageHeader({ title, description, actions, className, frontDoor, children, ...props }: PageHeaderProps) {
  const staggerDescription = frontDoor ? (
    <span className="animate-fade-up block" style={{ animationDelay: "90ms" }}>
      {description}
    </span>
  ) : (
    description
  );
  const header = (
    <div
      className={cn(
        "flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between",
        frontDoor && "relative",
        className
      )}
      {...props}
    >
      <div className="min-w-0 space-y-1">
        <h1 className="font-serif text-display-md font-medium text-balance">{title}</h1>
        {description && <p className="max-w-2xl text-sm text-muted-foreground">{staggerDescription}</p>}
        {children}
      </div>
      {actions && (
        <div
          className={cn(
            "flex shrink-0 flex-wrap items-center gap-2",
            frontDoor && "animate-fade-up"
          )}
          style={frontDoor ? { animationDelay: "160ms" } : undefined}
        >
          {actions}
        </div>
      )}
    </div>
  );

  if (!frontDoor) {
    return header;
  }

  return (
    <section className="animate-fade-up hairline relative overflow-hidden rounded-2xl border bg-card/60 shadow-card">
      {/* Light-theme ambient washes: static gradients, zero per-frame cost. */}
      <div
        aria-hidden
        className="pointer-events-none absolute -right-20 -top-24 h-64 w-64 rounded-full"
        style={{
          background:
            "radial-gradient(closest-side, color-mix(in oklch, var(--primary) 16%, transparent), transparent)",
        }}
      />
      <div
        aria-hidden
        className="pointer-events-none absolute -bottom-28 -left-24 h-64 w-64 rounded-full"
        style={{
          background:
            "radial-gradient(closest-side, color-mix(in oklch, var(--primary) 9%, transparent), transparent)",
        }}
      />
      {/* Dark-theme aurora: screen-blend light only ever composited over a dark surface. */}
      <div aria-hidden className="pointer-events-none absolute inset-0 hidden overflow-hidden dark:block">
        <span className="aurora-blob aurora-blob-1 opacity-30" />
        <span className="aurora-blob aurora-blob-2 opacity-30" />
        <div className="aurora-grid opacity-30" />
      </div>
      {/* Shimmer hairline crowns the band — the same premium separator the dashboard uses. */}
      <span aria-hidden className="shimmer-rule absolute inset-x-0 top-0 block h-px" />
      <div className="relative px-6 py-6">{header}</div>
    </section>
  );
}

export { PageHeader };
