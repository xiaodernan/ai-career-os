"use client";

import * as React from "react";
import { TriangleAlert, RotateCcw } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api/client";

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
  title = "Something went wrong",
  error,
  message,
  onRetry,
  retrying,
  className,
  ...props
}: ErrorStateProps) {
  const detail =
    message ??
    (error instanceof ApiError
      ? error.message
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
      <h3 className="text-sm font-semibold">{title}</h3>
      {detail && <p className="max-w-sm text-sm text-muted-foreground">{detail}</p>}
      {onRetry && (
        <Button variant="outline" size="sm" className="mt-3" onClick={onRetry} loading={retrying}>
          <RotateCcw aria-hidden />
          Try again
        </Button>
      )}
    </div>
  );
}

export { ErrorState };
