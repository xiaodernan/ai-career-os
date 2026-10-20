import * as React from "react";
import Link from "next/link";
import { ChevronRight, Quote } from "lucide-react";
import { cn } from "@/lib/utils";
import { AIBadge } from "./ai-badge";
import { useLocale } from "@/lib/i18n/locale-context";

/**
 * EvidenceCard — every AI conclusion must be traceable. Shows the supporting
 * quote, the source breadcrumb (Resume › Experience › Internship) and a jump slot.
 */
export interface EvidenceCardProps extends React.ComponentProps<"figure"> {
  quote: string;
  /** Breadcrumb path from the chunk metadata, e.g. ["Resume","Experience","Internship"] */
  sourcePath?: string[];
  docTitle?: string;
  /** Real in-app location to inspect the evidence (document viewer, resume section…) */
  href?: string;
  /** Rendered at the end of the header row (e.g. score, confidence) */
  accessory?: React.ReactNode;
  showAIBadge?: boolean;
}

function EvidenceCard({
  quote,
  sourcePath,
  docTitle,
  href,
  accessory,
  showAIBadge = true,
  className,
  children,
  ...props
}: EvidenceCardProps) {
  const { t } = useLocale();
  return (
    <figure
      className={cn(
        "rounded-lg border border-border/70 bg-muted/30 p-3.5 text-sm shadow-soft",
        className
      )}
      {...props}
    >
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
        <Quote className="size-3.5 shrink-0 text-primary/60" aria-hidden />
        <nav aria-label={t("evidence.source")} className="min-w-0 flex-1">
          {sourcePath && sourcePath.length > 0 ? (
            <ol className="flex flex-wrap items-center gap-0.5 text-xs text-muted-foreground">
              {sourcePath.map((crumb, i) => (
                <li key={`${crumb}-${i}`} className="flex items-center gap-0.5">
                  {i > 0 && <ChevronRight className="size-3 text-border" aria-hidden />}
                  <span className={cn("truncate", i === sourcePath.length - 1 && "text-foreground")}>
                    {crumb}
                  </span>
                </li>
              ))}
            </ol>
          ) : (
            docTitle && (
              <span className="truncate text-xs font-medium text-muted-foreground">{docTitle}</span>
            )
          )}
        </nav>
        {showAIBadge && <AIBadge />}
        {accessory}
      </div>

      <blockquote className="mt-2 border-l-2 border-primary/35 pl-3 leading-relaxed text-foreground italic">
        {quote}
      </blockquote>

      {href && (
        <div className="mt-2.5 flex justify-end">
          <Link
            href={href}
            className="text-xs font-medium text-primary underline-offset-4 hover:underline focus-visible:ring-[3px] focus-visible:ring-primary/30 rounded-md px-1 -mx-1"
          >
            {t("evidence.jumpToSource")} →
          </Link>
        </div>
      )}
      {children}
    </figure>
  );
}

export { EvidenceCard };
