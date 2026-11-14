import * as React from "react";
import { cn } from "@/lib/utils";

/**
 * PageSection — one named band inside a PageShell: a quiet h2 and its optional
 * sentence, an aria-labelled landmark section so a landmark reader hears the
 * page's structure, not a flat column of cards. Presentational only: no data,
 * no fetches.
 */
export interface PageSectionProps extends Omit<React.ComponentProps<"section">, "title"> {
  /** The band's name. Overrides the DOM `title` attribute slot deliberately. */
  title?: React.ReactNode;
  description?: React.ReactNode;
}

export function PageSection({ title, description, className, children, ...props }: PageSectionProps) {
  const ariaLabel = typeof title === "string" ? title : undefined;
  return (
    <section aria-label={ariaLabel} className={cn("flex flex-col gap-4", className)} {...props}>
      {(title || description) && (
        <div className="space-y-1">
          {title ? <h2 className="text-lg font-semibold tracking-tight text-foreground">{title}</h2> : null}
          {description ? <p className="max-w-2xl text-sm text-muted-foreground">{description}</p> : null}
        </div>
      )}
      {children}
    </section>
  );
}
