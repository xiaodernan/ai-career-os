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
