"use client";

import * as React from "react";
import { TriangleAlert, RotateCcw } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api/client";
import { describe } from "@/lib/hooks/failure";
import { useLocale } from "@/lib/i18n/locale-context";

/**
 * ErrorState — failure surface with a real retry affordance.
 */
export interface ErrorStateProps extends React.ComponentProps<"div"> {
  title?: string;
  error?: unknown;
  message?: string;
  onRetry?: () => void;
  retrying?: boolean;
}

function ErrorState({
  title,
  error,
  message,
  onRetry,
  retrying,
  className,
  ...props
}: ErrorStateProps) {
  const { t } = useLocale();
  const heading = title ?? t("common.somethingWentWrong");
  // The server's own English is not the sentence a reader should read: the code
  // names what happened, and the table has that sentence in the reader's language.
  const detail =
    message ??
    (error instanceof ApiError
      ? describe(error, "")
      : error instanceof Error
        ? error.message
        : undefined);

  return (
    <div
      role="alert"
      className={cn(
        "flex flex-col items-center justify-center gap-1 px-6 py-10 text-center",
        className
      )}
      {...props}
    >
      <div className="mb-2 flex size-11 items-center justify-center rounded-xl border border-destructive/25 bg-destructive/10 text-destructive [&_svg]:size-5">
        <TriangleAlert aria-hidden />
      </div>
      <h3 className="text-sm font-semibold">{heading}</h3>
      {detail && <p className="max-w-sm text-sm text-muted-foreground">{detail}</p>}
      {onRetry && (
        <Button variant="outline" size="sm" className="mt-3" onClick={onRetry} loading={retrying}>
          <RotateCcw aria-hidden />
          {t("common.tryAgain")}
        </Button>
      )}
    </div>
  );
}

export { ErrorState };
