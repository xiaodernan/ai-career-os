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
    <div className="flex min-h-dvh flex-col items-center justify-center gap-6 px-6 text-center">
      <span className="flex size-12 items-center justify-center rounded-xl bg-destructive/10 text-destructive shadow-soft">
        <RotateCcw className="size-6" aria-hidden />
      </span>
      <div className="max-w-md space-y-2">
        <h1 className="font-serif text-display-lg font-medium tracking-tight text-balance">
          {t("errors.couldNotStart")}
        </h1>
        <p className="text-sm leading-relaxed text-muted-foreground">
          {t("errors.couldNotStartDescription")}
        </p>
        {error.digest ? (
          <p className="font-mono text-xs text-muted-foreground/70">
            digest: {error.digest}
          </p>
        ) : null}
      </div>
      <Button onClick={reset}>
        <RotateCcw className="size-4" aria-hidden />
        {t("common.tryAgain")}
      </Button>
    </div>
  );
}
