"use client";

import { useEffect } from "react";
import { RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="flex min-h-dvh flex-col items-center justify-center gap-6 px-6 text-center">
      <span className="flex size-12 items-center justify-center rounded-xl bg-destructive/10 text-destructive shadow-soft">
        <RotateCcw className="size-6" aria-hidden />
      </span>
      <div className="max-w-md space-y-2">
        <h1 className="font-serif text-display-lg font-medium tracking-tight text-balance">
          Something broke on this screen.
        </h1>
        <p className="text-sm leading-relaxed text-muted-foreground">
          The error was logged to the console. Retrying re-renders the page
          without losing your session.
        </p>
        {error.digest ? (
          <p className="font-mono text-xs text-muted-foreground/70">
            digest: {error.digest}
          </p>
        ) : null}
      </div>
      <Button onClick={reset}>
        <RotateCcw className="size-4" aria-hidden />
        Try again
      </Button>
    </div>
  );
}
