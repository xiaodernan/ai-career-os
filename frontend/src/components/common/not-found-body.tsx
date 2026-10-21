"use client";

import * as React from "react";
import Link from "next/link";
import { Compass } from "lucide-react";
import { Button } from "@/components/ui/button";
import { LocaleSwitcher } from "@/components/common/locale-switcher";
import { useLocale } from "@/lib/i18n/locale-context";

/**
 * The 404 body, in the reader's language.
 *
 * It is a separate file from `app/not-found.tsx` because that page is a
 * server component, and the part that reads the locale -- and the part
 * that names the tab -- has to be a client one.
 *
 * The tab's title is set here rather than by the page's `metadata` export,
 * for one reason: only this component knows the route did not resolve. The
 * client-side title table answers `null` for a path the product does not
 * name, and this is what fills it in -- in the reader's language, where the
 * server could not have.
 *
 * The switch is here because this is a public page: a reader who arrived
 * on a broken link and cannot read English is also the reader who cannot
 * find the control that would fix it.
 */
export function NotFoundBody() {
  const { t, locale } = useLocale();

  React.useEffect(() => {
    document.title = `${t("common.pageNotFound")} · AI Career OS`;
  }, [t, locale]);

  return (
    <div className="flex min-h-dvh flex-col items-center justify-center gap-6 px-6 text-center">
      <span className="flex size-12 items-center justify-center rounded-xl bg-primary/10 text-primary shadow-soft">
        <Compass className="size-6" aria-hidden />
      </span>
      <div className="max-w-md space-y-2">
        <h1 className="font-serif text-display-lg font-medium tracking-tight text-balance">
          {t("errors.notOnTheMap")}
        </h1>
        <p className="text-sm leading-relaxed text-muted-foreground">
          {t("errors.notOnTheMapDescription")}
        </p>
      </div>
      <Button asChild>
        <Link href="/dashboard">{t("common.backToDashboard")}</Link>
      </Button>
      <LocaleSwitcher className="absolute top-4 right-4" />
    </div>
  );
}
