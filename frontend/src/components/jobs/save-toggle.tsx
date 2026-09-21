"use client";

import * as React from "react";
import { Bookmark } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { useToggleSaveJob } from "@/lib/hooks/actions";

/**
 * SaveToggle — optimistic saved-job affordance. Reflects `saved` from the API
 * and rolls back through the mutation hook when the request fails.
 */
export function SaveToggle({
  jobId,
  saved,
  size = "sm",
  withLabel = false,
  className,
  disabled,
}: {
  jobId: string;
  saved?: boolean;
  size?: "xs" | "sm" | "md";
  withLabel?: boolean;
  className?: string;
  disabled?: boolean;
}) {
  const toggle = useToggleSaveJob();
  const [pending, setPending] = React.useState(false);

  return (
    <Button
      type="button"
      variant={saved ? "ai" : "outline"}
      size={withLabel ? size : "icon-sm"}
      aria-pressed={Boolean(saved)}
      aria-label={saved ? "Remove from saved jobs" : "Save this job"}
      disabled={disabled || pending}
      className={cn(!withLabel && "shrink-0", className)}
      onClick={(e) => {
        e.preventDefault();
        e.stopPropagation();
        setPending(true);
        toggle.mutate(
          { id: jobId, saved: Boolean(saved) },
          { onSettled: () => setPending(false) }
        );
      }}
    >
      <Bookmark aria-hidden className={saved ? "fill-current" : undefined} />
      {withLabel && (saved ? "Saved" : "Save")}
    </Button>
  );
}
