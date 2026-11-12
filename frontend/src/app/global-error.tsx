"use client";

import { useEffect } from "react";
import { RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { LocaleProvider, useLocale } from "@/lib/i18n/locale-context";
import "./globals.css";

/**
 * The outermost boundary. Next renders this INSTEAD OF the root layout when
 * the layout itself throws, so it must supply its own <html> and <body> --
 * and its own globals.css import, because no parent stylesheet survives the
 * swap. The per-route error.tsx still handles everything short of that.
 *
 * The root layout is also what carries the locale provider, so this boundary
 * has to bring its own: a screen that replaces the shell and then throws on
 * a missing context is a screen that shows the wrong thing exactly when it
 * most needs to be right.
 *
 * Visually it carries the same front-door language as the other failure
 * surfaces (Epic 142): the aurora is fully decorative and hidden from AT,
 * the entrance is CSS-only stagger, and the copy stays the translated keys
 * the pages have always used. The one difference is intent: this is the
 * screen the reader sees when the app itself is wrong, so the reset button
 * is the only thing that matters — and it is shaped like every other
 * "something broke" door (glow-halo + glow-on-hover).
 */
export default function GlobalError({
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
    <html lang="en">
      <body className="min-h-dvh bg-background text-foreground">
        <LocaleProvider>
          <GlobalErrorBody error={error} reset={reset} />
        </LocaleProvider>
      </body>
    </html>
  );
}

function GlobalErrorBody({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const { t } = useLocale();
  return (
    <div className="relative flex min-h-dvh flex-col items-center justify-center overflow-hidden px-6 text-center">
      {/* Decorative aurora backdrop — the inner failure boundary wears the same language (Epic 142) */}
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
          {t("errors.couldNotStart")}
        </h1>
        <p
          className="animate-fade-up text-sm leading-relaxed text-muted-foreground"
          style={{ animationDelay: "160ms" }}
        >
          {t("errors.couldNotStartDescription")}
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
