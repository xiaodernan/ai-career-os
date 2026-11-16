"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ArrowRight,
  CheckCircle2,
  Clock,
  FileText,
  Gauge,
  MessageSquare,
  MoveRight,
  BookOpen,
  Sparkles,
  Target,
  TrendingUp,
  Users,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useLocale } from "@/lib/i18n/locale-context";
import { ProductPreview } from "@/components/marketing/product-preview";

/**
 * /tour — the ten-minute start (Epic 244).
 *
 * The public front door for the reader who wants to know what walking
 * through the door means before they register. Eight beats from signup to
 * the closing ceremony; each one names a real screen, with its honest cost
 * and its one action. It answers the only question a first-time reader
 * ever has: what do I actually do here, and in what order.
 */
const BEATS = [
  { icon: Sparkles, key: "register" },
  { icon: FileText, key: "resume" },
  { icon: Target, key: "job" },
  { icon: Gauge, key: "match" },
  { icon: TrendingUp, key: "tailor" },
  { icon: Users, key: "rehearse" },
  { icon: MessageSquare, key: "track" },
  { icon: MoveRight, key: "ceremony" },
  { icon: BookOpen, key: "afterward" },
] as const;

export default function TourPage() {
  const router = useRouter();
  const { t, locale, setLocale } = useLocale();

  return (
    <div className="relative min-h-dvh overflow-hidden bg-background">
      <div aria-hidden className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(55%_45%_at_50%_-5%,color-mix(in_oklch,var(--primary)_10%,transparent),transparent)]" />

      {/* Sticky header with brand + register CTA */}
      <header className="sticky top-0 z-50 border-b border-border/60 bg-background/80 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4">
          <Link href="/" className="flex items-center gap-2 font-serif font-semibold tracking-tight">
            <Sparkles className="size-4 text-primary" aria-hidden />
            <span>AI Career OS</span>
          </Link>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setLocale(locale === "en" ? "zh" : "en")}
              className="rounded-lg px-3 py-2 text-xs font-medium text-muted-foreground transition-colors hover:text-foreground focus-visible:ring-[3px] focus-visible:ring-ring/35"
            >
              {locale === "en" ? t("landing.switchToChinese") : t("landing.switchToEnglish")}
            </button>
            <Button variant="ai" size="sm" asChild className="glow-on-hover">
              <Link href="/register">
                {t("tour.cta")}
                <ArrowRight className="size-3.5" aria-hidden />
              </Link>
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 pb-24 pt-10 sm:pt-16">
        {/* Hero */}
        <div className="max-w-3xl">
          <p className="text-2xs font-semibold uppercase tracking-widest text-primary">
            {t("tour.eyebrow")}
          </p>
          <h1 className="mt-4 text-balance font-serif text-4xl font-semibold leading-[1.08] tracking-tight sm:text-5xl lg:text-6xl">
            {t("tour.title")}
          </h1>
          <p className="mt-5 max-w-2xl text-lg text-muted-foreground">{t("tour.description")}</p>
        </div>

        {/* Product at a glance — the same illustration the landing carries */}
        <figure className="mx-auto mt-12 max-w-4xl">
          <ProductPreview className="opacity-90" />
          <figcaption className="mt-3 text-center text-2xs text-muted-foreground">
            {t("tour.caption")}
          </figcaption>
        </figure>

        {/* The nine beats */}
        <ol className="mt-14 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {BEATS.map((beat, index) => {
            const Icon = beat.icon;
            return (
              <li key={beat.key}>
                <div
                  aria-label={t(`tour.beat_${beat.key}_title`)}
                  className="group block h-full rounded-2xl border border-border/60 bg-card/60 p-5 text-left transition-all duration-300 hover:border-primary/25 hover:bg-card hover:shadow-card focus-visible:ring-[3px] focus-visible:ring-primary/30"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-2xs tabular-nums font-semibold text-muted-foreground">
                      {String(index + 1).padStart(2, "0")}
                    </span>
                    <Icon aria-hidden className="size-5 text-primary" />
                    <h2 className="text-sm font-semibold leading-tight">
                      {t(`tour.beat_${beat.key}_title`)}
                    </h2>
                  </div>
                  <p className="mt-3 text-xs leading-relaxed text-muted-foreground">
                    {t(`tour.beat_${beat.key}_body`)}
                  </p>
                  <div className="mt-4 flex items-center gap-1.5 text-2xs font-medium text-primary opacity-80 transition-opacity duration-200 group-hover:opacity-100">
                    <Clock aria-hidden className="size-3" />
                    <span>{t(`tour.beat_${beat.key}_time`)}</span>
                  </div>
                </div>
              </li>
            );
          })}
        </ol>

        {/* Closing block — the whole arc in one glance */}
        <Card className="mt-12 border-primary/15 bg-gradient-to-br from-primary/[0.06] via-card to-card">
          <CardHeader>
            <CardTitle className="font-serif text-2xl font-semibold">{t("tour.closingTitle")}</CardTitle>
            <CardDescription className="mt-2 max-w-4xl text-base leading-relaxed">
              {t("tour.closingBody")}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {[
                { k: "tour.fact1_value", v: "tour.fact1_label" },
                { k: "tour.fact2_value", v: "tour.fact2_label" },
                { k: "tour.fact3_value", v: "tour.fact3_label" },
                { k: "tour.fact4_value", v: "tour.fact4_label" },
              ].map((item) => (
                <div key={item.k} className="rounded-xl border border-border/60 bg-background/50 p-4">
                  <dt className="text-2xs font-semibold uppercase tracking-widest text-muted-foreground">
                    {t(item.v)}
                  </dt>
                  <dd className="mt-1 font-serif text-2xl font-semibold tabular-nums">{t(item.k)}</dd>
                </div>
              ))}
            </dl>
            <div className="space-y-3">
              {[t("tour.note1"), t("tour.note2"), t("tour.note3")].map((line, i) => (
                <p key={i} className="flex items-start gap-2 text-sm leading-relaxed text-muted-foreground">
                  <CheckCircle2 aria-hidden className="mt-0.5 size-4 shrink-0 text-success" />
                  {line}
                </p>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Final CTA — two ways out */}
        <div className="mt-12 grid gap-4 sm:grid-cols-2">
          <Card className="p-6">
            <CardHeader className="p-0 pb-3">
              <CardTitle className="text-lg">{t("tour.pathOneTitle")}</CardTitle>
              <CardDescription className="text-sm leading-relaxed">
                {t("tour.pathOneBody")}
              </CardDescription>
            </CardHeader>
            <Button variant="ai" className="w-full glow-on-hover justify-between" onClick={() => router.push("/register")}>
              {t("tour.pathOneCta")}
              <ArrowRight aria-hidden className="size-4" />
            </Button>
          </Card>
          <Card className="p-6">
            <CardHeader className="p-0 pb-3">
              <CardTitle className="text-lg">{t("tour.pathTwoTitle")}</CardTitle>
              <CardDescription className="text-sm leading-relaxed">
                {t("tour.pathTwoBody")}
              </CardDescription>
            </CardHeader>
            <Button variant="outline" className="w-full justify-between" onClick={() => router.push("/playbook")}>
              {t("tour.pathTwoCta")}
              <ArrowRight aria-hidden className="size-4" />
            </Button>
          </Card>
        </div>
      </main>
    </div>
  );
}
