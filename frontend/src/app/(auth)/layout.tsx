"use client";

import Link from "next/link";
import { Sparkles } from "lucide-react";
import { ThemeToggle } from "@/components/common/theme-toggle";
import { LocaleSwitcher } from "@/components/common/locale-switcher";
import { useLocale } from "@/lib/i18n/locale-context";

/**
 * The four pillars the auth pages sell the product with.
 *
 * The keys are the copy; the table holds both languages. A visitor who
 * cannot read English lands here first, and this panel is what they are
 * asked to believe -- so it is the last panel that should be English-only.
 */
const PILLAR_KEYS = [
  "auth.pillars.knowledge.title",
  "auth.pillars.knowledge.text",
  "auth.pillars.matching.title",
  "auth.pillars.matching.text",
  "auth.pillars.fabrication.title",
  "auth.pillars.fabrication.text",
  "auth.pillars.interviews.title",
  "auth.pillars.interviews.text",
];

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  const { t } = useLocale();
  return (
    <div className="grid min-h-dvh lg:grid-cols-[1.05fr_1fr]">
      {/* Marketing panel */}
      <section className="relative hidden flex-col justify-between border-r border-border/70 bg-sidebar p-12 lg:flex">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(60%_50%_at_20%_0%,color-mix(in_oklch,var(--primary)_7%,transparent),transparent)]" aria-hidden />
        <Link
          href="/"
          className="relative flex items-center gap-2 outline-none focus-visible:ring-[3px] focus-visible:ring-ring/35 rounded-lg w-fit"
        >
          <span className="flex size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-soft">
            <Sparkles className="size-4.5" aria-hidden />
          </span>
          <span className="font-serif text-lg font-semibold tracking-tight">
            Career<span className="text-primary">OS</span>
          </span>
        </Link>

        <div className="relative max-w-md space-y-10">
          <div>
            <p className="mb-3 text-xs font-medium tracking-widest text-primary uppercase">
              {t("auth.eyebrow")}
            </p>
            <h1 className="font-serif text-display-lg leading-[1.08] font-medium text-balance">
              {t("auth.headline")}
            </h1>
            <p className="mt-4 text-sm leading-relaxed text-muted-foreground">
              {t("auth.description")}
            </p>
          </div>

          <ul className="space-y-5">
            {PILLAR_KEYS.map((key, i) => (
              <li key={key} className="flex gap-3">
                <span aria-hidden className="mt-1.5 size-1.5 shrink-0 rounded-full bg-primary/70" />
                <div>
                  <p className="text-sm font-medium">{t(`${key}.title`)}</p>
                  <p className="text-sm text-muted-foreground">{t(`${key}.text`)}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>

        <p className="relative text-xs text-muted-foreground">
          {t("auth.quote")}
        </p>
      </section>

      {/* Form panel */}
      <section className="relative flex flex-col">
        <div className="flex justify-end p-4 lg:hidden">
          <Link href="/" className="flex items-center gap-2 font-serif font-semibold">
            <span className="flex size-7 items-center justify-center rounded-lg bg-primary text-primary-foreground">
              <Sparkles className="size-4" aria-hidden />
            </span>
            CareerOS
          </Link>
        </div>
        <div className="absolute top-4 right-4 hidden items-center gap-1 lg:flex">
          <ThemeToggle />
          <LocaleSwitcher />
        </div>
        <div className="mx-auto flex w-full max-w-sm flex-1 flex-col justify-center px-6 pb-16">
          <div className="animate-fade-up">{children}</div>
        </div>
        <div className="flex items-center justify-between px-6 pb-6 text-xs text-muted-foreground lg:px-12">
          <div className="flex items-center gap-1">
            <ThemeToggle className="lg:hidden" />
            <LocaleSwitcher className="lg:hidden" />
          </div>
          <span className="ml-auto">© {new Date().getFullYear()} AI Career OS</span>
        </div>
      </section>
    </div>
  );
}
