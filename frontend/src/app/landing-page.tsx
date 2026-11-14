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
import { ProductPreview } from "@/components/marketing/product-preview";
import { AuroraBackground } from "@/components/ui/aurora";
import { Reveal } from "@/components/ui/reveal";
import { GradientText } from "@/components/ui/gradient-text";

/**
 * The marketing landing page (18.2): a public-facing page that introduces
 * AI Career OS and links to the app.
 *
 * It is a client component because the copy reads from the locale table -- the
 * same table every signed-in surface reads. A public visitor who cannot switch
 * the language has no way to read the product's front door in their own
 * language, so the switch travels with the page.
 *
 * The visual layer (aurora hero, glass cards, scroll reveals) is additive:
 * every animation degrades gracefully under `prefers-reduced-motion` and the
 * copy still reads from the locale table, so the copy gate is unchanged.
 */
export function LandingPage() {
  const { t, locale, setLocale } = useLocale();

  return (
    <div className="relative min-h-dvh overflow-hidden bg-background">
      <AuroraBackground />

      {/* Header — frosted, sticky, never competes with the hero. */}
      <header className="sticky top-0 z-50 glass">
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
              // The visible label and the accessible name are one thing; no aria
              // override, because the glyph alone named a control in two
              // languages and matched neither (WCAG 2.5.3, Lighthouse 1.0 now).
            >
              <Globe aria-hidden />
              <span className="hidden sm:inline">
                {locale === "en" ? t("landing.switchToChinese") : t("landing.switchToEnglish")}
              </span>
            </Button>
            <Button variant="ghost" size="sm" asChild>
              <Link href="/login">{t("landing.signIn")}</Link>
            </Button>
            <Button variant="ai" size="sm" asChild className="glow-on-hover">
              <Link href="/register">
                {t("landing.getStarted")}
                <ArrowRight className="size-3.5" aria-hidden />
              </Link>
            </Button>
          </div>
        </div>
      </header>

      <main>
      {/* Hero */}
      <section className="relative mx-auto max-w-6xl px-4 pt-16 text-center sm:pt-24">
        <Reveal className="mx-auto max-w-3xl">
          <span className="inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/5 px-4 py-1.5 text-sm font-medium text-primary">
            <span className="size-1.5 rounded-full bg-primary animate-pulse-dot" aria-hidden />
            {t("landing.eyebrow")}
          </span>
          <h1 className="mt-6 font-serif text-4xl font-semibold leading-[1.05] tracking-tight sm:text-5xl lg:text-7xl">
            {t("landing.heroTitle")}
            <GradientText>{t("landing.heroTitleAccent")}</GradientText>
            <br />
            {t("landing.heroTitleTail")}
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-lg text-muted-foreground">
            {t("landing.heroDescription")}
          </p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <Button variant="ai" size="lg" asChild className="glow-on-hover">
              <Link href="/register">
                {t("landing.startFree")}
                <ArrowRight className="size-4" aria-hidden />
              </Link>
            </Button>
            <Button variant="outline" size="lg" asChild>
              <Link href="/login">{t("landing.signIn")}</Link>
            </Button>
          </div>
          <p className="mx-auto mt-5 flex max-w-xl items-center justify-center gap-2 text-sm text-muted-foreground">
            <Shield className="size-4 text-primary" aria-hidden />
            {t("landing.heroBadge")}
          </p>
        </Reveal>

        {/* Live stats band — a glass strip under the hero. */}
        <Reveal delay={120} className="mx-auto mt-12 max-w-3xl">
          <div className="glass grid grid-cols-3 divide-x divide-border/60 rounded-2xl px-2 py-5 shadow-card">
            <Stat value="12K+" label={t("landing.stat1Label")} />
            <Stat value="8" label={t("landing.stat2Label")} />
            <Stat value="100%" label={t("landing.stat3Label")} />
          </div>
        </Reveal>

        {/* The product at work — framed in glass, gently floating. */}
        <Reveal delay={200} className="mx-auto mt-14 max-w-4xl">
          <div className="glass-strong float-soft rounded-3xl p-3">
            <ProductPreview className="overflow-hidden rounded-2xl" />
          </div>
        </Reveal>
      </section>

      {/* Features */}
      <section className="relative mt-24 border-t border-border/50 bg-muted/30">
        <div className="mx-auto max-w-6xl px-4 py-20">
          <Reveal className="mx-auto max-w-2xl text-center">
            <h2 className="font-serif text-3xl font-semibold tracking-tight sm:text-4xl">
              {t("landing.featuresTitle")}
            </h2>
            <p className="mt-3 text-muted-foreground">{t("landing.featuresDescription")}</p>
          </Reveal>
          <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            <FeatureCard delay={0} icon={<FileText className="size-5" aria-hidden />} title={t("landing.features.resume")} description={t("landing.features.resumeDescription")} />
            <FeatureCard delay={80} icon={<Target className="size-5" aria-hidden />} title={t("landing.features.matching")} description={t("landing.features.matchingDescription")} />
            <FeatureCard delay={160} icon={<MessageSquare className="size-5" aria-hidden />} title={t("landing.features.interviews")} description={t("landing.features.interviewsDescription")} />
            <FeatureCard delay={0} icon={<Briefcase className="size-5" aria-hidden />} title={t("landing.features.tracker")} description={t("landing.features.trackerDescription")} />
            <FeatureCard delay={80} icon={<TrendingUp className="size-5" aria-hidden />} title={t("landing.features.growth")} description={t("landing.features.growthDescription")} />
            <FeatureCard delay={160} icon={<BarChart3 className="size-5" aria-hidden />} title={t("landing.features.analytics")} description={t("landing.features.analyticsDescription")} />
          </div>
        </div>
      </section>

      {/* Trust */}
      <section className="relative border-t border-border/50">
        <div className="mx-auto max-w-6xl px-4 py-20">
          <div className="grid gap-8 sm:grid-cols-3">
            <Reveal delay={0}>
              <TrustItem icon={<Shield className="size-5" aria-hidden />} title={t("landing.trust.evidence")} description={t("landing.trust.evidenceDescription")} />
            </Reveal>
            <Reveal delay={100}>
              <TrustItem icon={<Users className="size-5" aria-hidden />} title={t("landing.trust.scoped")} description={t("landing.trust.scopedDescription")} />
            </Reveal>
            <Reveal delay={200}>
              <TrustItem icon={<CheckCircle2 className="size-5" aria-hidden />} title={t("landing.trust.inspectable")} description={t("landing.trust.inspectableDescription")} />
            </Reveal>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="relative border-t border-border/50">
        <div className="mx-auto max-w-6xl px-4 py-20">
          <Reveal className="glass-strong relative overflow-hidden rounded-3xl px-6 py-16 text-center">
            <span aria-hidden className="aurora-blob aurora-blob-2 !opacity-30 !blur-3xl" />
            <h2 className="relative font-serif text-3xl font-semibold tracking-tight sm:text-4xl">
              {t("landing.ctaTitle")}
            </h2>
            <p className="relative mx-auto mt-3 max-w-xl text-muted-foreground">
              {t("landing.ctaDescription")}
            </p>
            <div className="relative mt-8">
              <Button variant="ai" size="lg" asChild className="glow-on-hover">
                <Link href="/register">
                  {t("landing.ctaButton")}
                  <ArrowRight className="size-4" aria-hidden />
                </Link>
              </Button>
            </div>
          </Reveal>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border/50">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 text-sm text-muted-foreground">
          <span>© 2026 AI Career OS</span>
          <span>{t("landing.footerNote")}</span>
        </div>
      </footer>
      </main>
    </div>
  );
}

function Stat({ value, label }: { value: string; label: string }) {
  return (
    <div className="px-3 text-center">
      <div className="font-serif text-3xl font-semibold tracking-tight text-foreground sm:text-4xl">
        {value}
      </div>
      <div className="mt-1 text-xs text-muted-foreground sm:text-sm">{label}</div>
    </div>
  );
}

function FeatureCard({
  icon,
  title,
  description,
  delay = 0,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
  delay?: number;
}) {
  return (
    <Reveal delay={delay}>
      <Card className="card-lift group h-full overflow-hidden transition-shadow duration-300 hover:shadow-pop">
        <CardContent className="p-6">
          <span className="flex size-11 items-center justify-center rounded-xl bg-primary/10 text-primary ring-1 ring-inset ring-primary/15 transition-transform duration-300 group-hover:scale-110 group-hover:bg-primary group-hover:text-primary-foreground">
            {icon}
          </span>
          <h3 className="mt-4 font-semibold">{title}</h3>
          <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{description}</p>
        </CardContent>
      </Card>
    </Reveal>
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
      <span className="mx-auto flex size-12 items-center justify-center rounded-full bg-primary/10 text-primary ring-1 ring-inset ring-primary/15">
        {icon}
      </span>
      <h3 className="mt-4 font-semibold">{title}</h3>
      <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{description}</p>
    </div>
  );
}
