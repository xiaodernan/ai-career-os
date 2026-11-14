"use client";

import Link from "next/link";
import { Compass } from "lucide-react";
import { Button } from "@/components/ui/button";
import { LocaleSwitcher } from "@/components/common/locale-switcher";
import { useLocale } from "@/lib/i18n/locale-context";

/**
 * The 404 body, in the reader's language.
 *
 * It is a separate file from `app/not-found.tsx` because that page is a
 * server component, and the part that reads the locale has to be a client
 * one.
 *
 * The tab's title is the server's: the 404 page is the one route where
 * the server knows more than the browser does — it knows the route did
 * not resolve, which the browser cannot tell from the path alone — and
 * the locale travels in a cookie so the server can name it in the
 * reader's language.
 *
 * The switch is here because this is a public page: a reader who arrived
 * on a broken link and cannot read English is also the reader who cannot
 * find the control that would fix it.
 *
 * The lost page gets the same front-door language the anonymous surfaces
 * carry (Epic 142): the aurora, the ghost numeral, the glow ring on the
 * compass, the staggered CSS-only entrance — no IntersectionObserver, no
 * new copy, nothing that needs JS to become visible; the reduced-motion
 * blanket forces every layer visible.
 */
export function NotFoundBody() {
  const { t } = useLocale();
  return (
    <div className="relative flex min-h-dvh flex-col items-center justify-center overflow-hidden px-6 text-center">
      {/* Decorative aurora backdrop — the same three blobs and grid the landing and auth doors use */}
      <div aria-hidden className="aurora-bg pointer-events-none absolute inset-0 -z-10 overflow-hidden">
        <span className="aurora-blob aurora-blob-1" />
        <span className="aurora-blob aurora-blob-2" />
        <span className="aurora-blob aurora-blob-3" />
        <div className="aurora-grid" />
      </div>

      {/* Ghost 404 numeral — aria-hidden; the heading is the announcement */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 flex select-none items-center justify-center font-serif font-semibold leading-none tracking-tighter text-primary/[0.07] text-[38vw] sm:text-[30vw] lg:text-[22rem]"
      >
        404
      </div>

      {/* Shimmer rule above the icon */}
      <span
        aria-hidden
        className="shimmer-rule mb-6 block h-px w-40"
      />

      <span className="animate-fade-up flex size-14 items-center justify-center rounded-2xl border border-primary/25 bg-primary/10 text-primary shadow-halo">
        <Compass className="size-7" aria-hidden />
      </span>

      <div className="max-w-md space-y-3">
        <h1
          className="animate-fade-up font-serif text-display-lg font-medium tracking-tight text-balance"
          style={{ animationDelay: "90ms" }}
        >
          {t("errors.notOnTheMap")}
        </h1>
        <p
          className="animate-fade-up text-sm leading-relaxed text-muted-foreground"
          style={{ animationDelay: "160ms" }}
        >
          {t("errors.notOnTheMapDescription")}
        </p>
      </div>

      <div className="animate-fade-up mt-2 flex flex-wrap items-center justify-center gap-2" style={{ animationDelay: "240ms" }}>
        <Button asChild variant="ai" size="lg" className="glow-halo glow-on-hover">
          <Link href="/dashboard">{t("common.backToDashboard")}</Link>
        </Button>
        <Button asChild variant="outline" size="lg">
          <Link href="/playbook">{t("nav.playbook")}</Link>
        </Button>
      </div>

      <LocaleSwitcher className="absolute top-4 right-4" />
    </div>
  );
}
