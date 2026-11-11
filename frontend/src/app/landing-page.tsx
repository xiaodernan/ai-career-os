"use client";

import * as React from "react";
import Link from "next/link";
import {
  ArrowRight,
  BarChart3,
  Briefcase,
  CheckCircle2,
  FileText,
  Globe,
  MessageSquare,
  Shield,
  Sparkles,
  Target,
  TrendingUp,
  Users,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useLocale } from "@/lib/i18n/locale-context";

/**
 * The marketing landing page (18.2): a public-facing page that introduces
 * AI Career OS and links to the app.
 *
 * It is a client component because the copy reads from the locale table -- the
 * same table every signed-in surface reads. A public visitor who cannot switch
 * the language has no way to read the product's front door in their own
 * language, so the switch travels with the page.
 */
export function LandingPage() {
  const { t, locale, setLocale } = useLocale();

  return (
    <div className="min-h-dvh bg-background">
      {/* Header */}
      <header className="border-b border-border/50">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4">
          <div className="flex items-center gap-2">
            <span className="flex size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
              <Sparkles className="size-4" aria-hidden />
            </span>
            <span className="font-serif text-lg font-semibold tracking-tight">
              Career<span className="text-primary">OS</span>
            </span>
          </div>
          <div className="flex items-center gap-3">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setLocale(locale === "en" ? "zh" : "en")}
              aria-label={
                locale === "en" ? t("landing.switchToChinese") : t("landing.switchToEnglish")
              }
            >
              <Globe aria-hidden />
              <span className="hidden sm:inline">{locale === "en" ? "中文" : "EN"}</span>
            </Button>
            <Button variant="ghost" size="sm" asChild>
              <Link href="/auth/login">{t("landing.signIn")}</Link>
            </Button>
            <Button variant="ai" size="sm" asChild>
              <Link href="/auth/register">
                {t("landing.getStarted")}
                <ArrowRight className="size-3.5" aria-hidden />
              </Link>
            </Button>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="mx-auto max-w-6xl px-4 py-20 text-center">
        <div className="mx-auto max-w-3xl">
          <h1 className="font-serif text-4xl font-semibold tracking-tight sm:text-5xl lg:text-6xl">
            {t("landing.heroTitle")}
            <span className="text-primary">{t("landing.heroTitleAccent")}</span>
            <br />
            {t("landing.heroTitleTail")}
          </h1>
          <p className="mt-6 text-lg text-muted-foreground">{t("landing.heroDescription")}</p>
          <div className="mt-8 flex items-center justify-center gap-3">
            <Button variant="ai" size="lg" asChild>
              <Link href="/auth/register">
                {t("landing.startFree")}
                <ArrowRight className="size-4" aria-hidden />
              </Link>
            </Button>
            <Button variant="outline" size="lg" asChild>
              <Link href="/auth/login">{t("landing.signIn")}</Link>
            </Button>
          </div>

        </div>
        {/* A static illustration of the product at work -- drawn with the product's own
            tokens, labelled as an illustration rather than faked as a screenshot. It exists
            so the front door shows the system instead of only claiming it. */}
          <figure
            role="img"
            aria-label={t("landing.preview.label")}
            className="animate-fade-up mx-auto mt-14 max-w-4xl text-left"
          >
            <div className="overflow-hidden rounded-2xl border border-border/70 bg-card shadow-pop">
              {/* window chrome */}
              <div
                className="flex items-center gap-1.5 border-b border-border/60 bg-muted/40 px-4 py-2.5"
                aria-hidden
              >
                <span className="size-2.5 rounded-full bg-red-400/70" />
                <span className="size-2.5 rounded-full bg-amber-400/70" />
                <span className="size-2.5 rounded-full bg-emerald-400/70" />
                <span className="ml-2 text-2xs tabular-nums text-muted-foreground">
                  careeros.app/applications
                </span>
              </div>
              <div className="grid gap-3 p-4 sm:grid-cols-[minmax(0,1fr)_11rem] sm:p-5">
                {/* the board, at a glance */}
                <div className="grid grid-cols-3 gap-2 sm:gap-3" aria-hidden>
                  {[
                    { label: t("landing.preview.applied"), count: 3, cards: 2 },
                    { label: t("landing.preview.interview"), count: 2, cards: 2 },
                    { label: t("landing.preview.offer"), count: 1, cards: 1 },
                  ].map((col) => (
                    <div
                      key={col.label}
                      className="flex flex-col gap-2 rounded-xl border border-border/60 bg-muted/30 p-2 sm:p-2.5"
                    >
                      <div className="flex items-center justify-between px-0.5 text-2xs font-semibold uppercase tracking-wide text-muted-foreground">
                        <span className="truncate">{col.label}</span>
                        <span className="tabular-nums">{col.count}</span>
                      </div>
                      {Array.from({ length: col.cards }).map((_, i) => (
                        <div
                          key={i}
                          className="space-y-1.5 rounded-lg border border-border/60 bg-background/80 p-2"
                        >
                          <div className="h-2 w-4/5 rounded bg-muted-foreground/25" />
                          <div className="h-2 w-3/5 rounded bg-muted-foreground/20" />
                          <div className="mt-1 flex items-center gap-1 pt-0.5">
                            <div className="h-4 w-10 rounded-full bg-primary/15" />
                            <div className="h-2 w-6 rounded bg-muted-foreground/15" />
                          </div>
                        </div>
                      ))}
                    </div>
                  ))}
                </div>
                {/* the match panel, at a glance */}
                <div
                  className="flex flex-col items-center justify-center gap-2 rounded-xl border border-border/60 bg-muted/30 p-4"
                  aria-hidden
                >
                  <div
                    className="flex size-20 items-center justify-center rounded-full"
                    style={{
                      background:
                        "conic-gradient(var(--primary) 0 331deg, color-mix(in oklch, var(--primary) 14%, transparent) 331deg 360deg)",
                    }}
                  >
                    <div className="flex size-16 flex-col items-center justify-center rounded-full bg-card">
                      <span className="text-lg font-semibold tabular-nums leading-none">92</span>
                      <span className="text-[10px] uppercase tracking-wide text-muted-foreground">
                        {t("landing.preview.match")}
                      </span>
                    </div>
                  </div>
                  <div className="w-full space-y-1.5">
                    <div className="h-1.5 w-full rounded bg-muted-foreground/20" />
                    <div className="h-1.5 w-4/5 rounded bg-muted-foreground/20" />
                    <div className="h-1.5 w-3/5 rounded bg-muted-foreground/20" />
                  </div>
                </div>
              </div>
              {/* the copilot's doorway */}
              <div
                className="flex items-center gap-2 border-t border-border/60 bg-background/60 px-4 py-3 text-sm text-muted-foreground"
                aria-hidden
              >
                <Sparkles className="size-4 shrink-0 text-primary" />
                <span className="truncate">{t("landing.preview.copilot")}</span>
                <ArrowRight className="ml-auto size-4 shrink-0" />
              </div>
            </div>
          </figure>
      </section>

      {/* Features */}
      <section className="border-t border-border/50 bg-muted/30">
        <div className="mx-auto max-w-6xl px-4 py-20">
          <h2 className="text-center font-serif text-3xl font-semibold tracking-tight">
            {t("landing.featuresTitle")}
          </h2>
          <p className="mx-auto mt-3 max-w-2xl text-center text-muted-foreground">
            {t("landing.featuresDescription")}
          </p>
          <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            <FeatureCard
              icon={<FileText className="size-5" aria-hidden />}
              title={t("landing.features.resume")}
              description={t("landing.features.resumeDescription")}
            />
            <FeatureCard
              icon={<Target className="size-5" aria-hidden />}
              title={t("landing.features.matching")}
              description={t("landing.features.matchingDescription")}
            />
            <FeatureCard
              icon={<MessageSquare className="size-5" aria-hidden />}
              title={t("landing.features.interviews")}
              description={t("landing.features.interviewsDescription")}
            />
            <FeatureCard
              icon={<Briefcase className="size-5" aria-hidden />}
              title={t("landing.features.tracker")}
              description={t("landing.features.trackerDescription")}
            />
            <FeatureCard
              icon={<TrendingUp className="size-5" aria-hidden />}
              title={t("landing.features.growth")}
              description={t("landing.features.growthDescription")}
            />
            <FeatureCard
              icon={<BarChart3 className="size-5" aria-hidden />}
              title={t("landing.features.analytics")}
              description={t("landing.features.analyticsDescription")}
            />
          </div>
        </div>
      </section>

      {/* Trust */}
      <section className="border-t border-border/50">
        <div className="mx-auto max-w-6xl px-4 py-20">
          <div className="grid gap-8 sm:grid-cols-3">
            <TrustItem
              icon={<Shield className="size-5" aria-hidden />}
              title={t("landing.trust.evidence")}
              description={t("landing.trust.evidenceDescription")}
            />
            <TrustItem
              icon={<Users className="size-5" aria-hidden />}
              title={t("landing.trust.scoped")}
              description={t("landing.trust.scopedDescription")}
            />
            <TrustItem
              icon={<CheckCircle2 className="size-5" aria-hidden />}
              title={t("landing.trust.inspectable")}
              description={t("landing.trust.inspectableDescription")}
            />
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="border-t border-border/50 bg-primary/5">
        <div className="mx-auto max-w-6xl px-4 py-20 text-center">
          <h2 className="font-serif text-3xl font-semibold tracking-tight">
            {t("landing.ctaTitle")}
          </h2>
          <p className="mx-auto mt-3 max-w-xl text-muted-foreground">
            {t("landing.ctaDescription")}
          </p>
          <div className="mt-8">
            <Button variant="ai" size="lg" asChild>
              <Link href="/auth/register">
                {t("landing.ctaButton")}
                <ArrowRight className="size-4" aria-hidden />
              </Link>
            </Button>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border/50">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 text-sm text-muted-foreground">
          <span>© 2026 AI Career OS</span>
          <span>{t("landing.footerNote")}</span>
        </div>
      </footer>
    </div>
  );
}

function FeatureCard({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
}) {
  return (
    <Card>
      <CardContent className="p-6">
        <span className="flex size-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
          {icon}
        </span>
        <h3 className="mt-4 font-semibold">{title}</h3>
        <p className="mt-2 text-sm text-muted-foreground">{description}</p>
      </CardContent>
    </Card>
  );
}

function TrustItem({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
}) {
  return (
    <div className="text-center">
      <span className="mx-auto flex size-12 items-center justify-center rounded-full bg-primary/10 text-primary">
        {icon}
      </span>
      <h3 className="mt-4 font-semibold">{title}</h3>
      <p className="mt-2 text-sm text-muted-foreground">{description}</p>
    </div>
  );
}
