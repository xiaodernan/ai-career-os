"use client";

import { useEffect } from "react";
import { RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useLocale } from "@/lib/i18n/locale-context";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const { t } = useLocale();
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="relative flex min-h-dvh flex-col items-center justify-center overflow-hidden px-6 text-center">
      {/* Decorative aurora backdrop — same front-door language as the 404 (Epic 142) */}
      <div aria-hidden className="aurora-bg pointer-events-none absolute inset-0 -z-10 overflow-hidden">
        <span className="aurora-blob aurora-blob-1" />
        <span className="aurora-blob aurora-blob-2" />
        <span className="aurora-blob aurora-blob-3" />
        <div className="aurora-grid" />
      </div>

      <span aria-hidden className="shimmer-rule mb-6 block h-px w-40" />

      <span className="animate-fade-up flex size-14 items-center justify-center rounded-2xl border border-destructive/25 bg-destructive/10 text-destructive shadow-soft">
        <RotateCcw className="size-7" aria-hidden />
      </span>
      <div className="max-w-md space-y-3">
        <h1
          className="animate-fade-up font-serif text-display-lg font-medium tracking-tight text-balance"
          style={{ animationDelay: "90ms" }}
        >
          {t("errors.brokeOnThisScreen")}
        </h1>
        <p
          className="animate-fade-up text-sm leading-relaxed text-muted-foreground"
          style={{ animationDelay: "160ms" }}
        >
          {t("errors.brokeOnThisScreenDescription")}
        </p>
        {error.digest ? (
          <p
            className="animate-fade-up font-mono text-xs text-muted-foreground/70"
            style={{ animationDelay: "200ms" }}
          >
            digest: {error.digest}
          </p>
        ) : null}
      </div>
      <div className="animate-fade-up mt-2" style={{ animationDelay: "240ms" }}>
        <Button variant="ai" size="lg" className="glow-halo glow-on-hover" onClick={reset}>
          <RotateCcw className="size-4" aria-hidden />
          {t("common.tryAgain")}
        </Button>
      </div>
    </div>
  );
}
