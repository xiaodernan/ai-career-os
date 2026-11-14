"use client";

import * as React from "react";
import Link from "next/link";
import {
  ArrowRight,
  BookOpen,
  Briefcase,
  CheckCircle2,
  ClipboardList,
  FileText,
  Globe,
  Keyboard,
  Mic,
  Printer,
  Sparkles,
  TrendingUp,
  Trophy,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { useLocale } from "@/lib/i18n/locale-context";

/**
 * /playbook — the reader's manual (Epic 214).
 *
 * A long-form, bilingual document for the whole loop: from registering to the
 * closing ceremony. Structured as chapters with headings, real names, and the
 * rules the AI plays by — because a manual that says less is a manual the
 * reader won't trust.
 *
 * The page is public (people will find it from search) but carries no product
 * data — every word here is a documented fact about how this product behaves.
 * Print rules collapse the chrome and go straight to the body.
 */

const SECTION_ICON_CLASS = "flex size-10 shrink-0 items-center justify-center rounded-xl border";

export default function PlaybookPage() {
  const { t, locale, setLocale } = useLocale();
  const print = () => window.print();

  return (
    <div className="relative min-h-dvh overflow-hidden bg-background">
      <header className="sticky top-0 z-50 border-b border-border/60 bg-background/80 backdrop-blur-md print:hidden">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4">
          <div className="flex items-center gap-2">
            <Link href="/" className="flex items-center gap-2 outline-none focus-visible:ring-[3px] focus-visible:ring-ring/35 rounded-lg">
              <span className="flex size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                <Sparkles className="size-4" aria-hidden />
              </span>
              <span className="font-serif text-lg font-semibold tracking-tight">
                Career<span className="text-primary">OS</span>
              </span>
            </Link>
            <span aria-hidden className="ml-2 hidden text-sm text-muted-foreground sm:inline">
              / playbook
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setLocale(locale === "en" ? "zh" : "en")}
              className="gap-1.5 text-muted-foreground"
            >
              <Globe aria-hidden className="size-4" />
              <span className="hidden sm:inline">{locale === "en" ? "中文" : "EN"}</span>
            </Button>
            <Button variant="ghost" size="sm" asChild>
              <Link href="/login">{t("landing.signIn")}</Link>
            </Button>
            <Button variant="ai" size="sm" asChild className="glow-on-hover">
              <Link href="/register">
                {t("landing.getStarted")}
                <ArrowRight className="size-4" aria-hidden />
              </Link>
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 pb-24">
        {/* Hero / cover */}
        <section className="space-y-6 pt-14">
          <p className="text-xs font-medium uppercase tracking-[0.3em] text-primary">
            {t("playbook.eyebrow")}
          </p>
          <h1 className="max-w-4xl font-serif text-5xl font-semibold leading-[1.05] tracking-tight sm:text-6xl">
            {t("playbook.title")}
          </h1>
          <p className="max-w-3xl text-lg text-muted-foreground">{t("playbook.description")}</p>
          <p className="text-xs uppercase tracking-widest text-muted-foreground">{t("playbook.dateLine")}</p>
        </section>

        {/* The loop */}
        <section id="loop" className="mt-14 space-y-6 border-t border-border/50 pt-14">
          <div className="flex flex-wrap items-baseline justify-between gap-3">
            <p className="text-2xs font-semibold uppercase tracking-widest text-primary">{t("playbook.loopEyebrow")}</p>
            <span className="text-2xs tabular-nums text-muted-foreground">01</span>
          </div>
          <h2 className="font-serif text-3xl font-semibold tracking-tight">{t("playbook.loopTitle")}</h2>
          <p className="max-w-4xl text-base leading-relaxed text-foreground/90">{t("playbook.loopBody")}</p>
        </section>

        {/* Quickstart */}
        <section id="quickstart" className="mt-14 space-y-6 border-t border-border/50 pt-14">
          <div className="flex flex-wrap items-baseline justify-between gap-3">
            <p className="text-2xs font-semibold uppercase tracking-widest text-primary">{t("playbook.quickstartEyebrow")}</p>
            <span className="text-2xs tabular-nums text-muted-foreground">02</span>
          </div>
          <h2 className="font-serif text-3xl font-semibold tracking-tight">{t("playbook.quickstartTitle")}</h2>
          <ol className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {[
              { n: 1, title: t("playbook.quick1Title"), body: t("playbook.quick1Body"), icon: Sparkles },
              { n: 2, title: t("playbook.quick2Title"), body: t("playbook.quick2Body"), icon: FileText },
              { n: 3, title: t("playbook.quick3Title"), body: t("playbook.quick3Body"), icon: Briefcase },
              { n: 4, title: t("playbook.quick4Title"), body: t("playbook.quick4Body"), icon: Mic },
              { n: 5, title: t("playbook.quick5Title"), body: t("playbook.quick5Body"), icon: ClipboardList },
            ].map((step) => {
              const Icon = step.icon;
              return (
                <li key={step.n} className="flex flex-col gap-2 rounded-2xl border border-border/60 bg-card/60 p-5">
                  <span className="flex size-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
                    <Icon aria-hidden className="size-4" />
                  </span>
                  <p className="text-sm font-semibold">
                    <span className="mr-2 text-muted-foreground">0{step.n} ·</span>
                    {step.title}
                  </p>
                  <p className="text-xs leading-relaxed text-muted-foreground">{step.body}</p>
                </li>
              );
            })}
          </ol>
        </section>

        {/* The map of the product */}
        <section id="surfaces" className="mt-14 space-y-6 border-t border-border/50 pt-14">
          <div className="flex flex-wrap items-baseline justify-between gap-3">
            <p className="text-2xs font-semibold uppercase tracking-widest text-primary">{t("playbook.surfacesEyebrow")}</p>
            <span className="text-2xs tabular-nums text-muted-foreground">03</span>
          </div>
          <h2 className="font-serif text-3xl font-semibold tracking-tight">{t("playbook.surfacesTitle")}</h2>
          <div className="grid gap-4 md:grid-cols-2">
            {[
              { eyebrow: "find", title: t("playbook.surfacesFind"), body: t("playbook.surfacesFindBody"), icon: Briefcase, tint: "text-primary border-primary/25 bg-primary/10" },
              { eyebrow: "prepare", title: t("playbook.surfacesPrepare"), body: t("playbook.surfacesPrepareBody"), icon: BookOpen, tint: "text-success border-success/25 bg-success/10" },
              { eyebrow: "track", title: t("playbook.surfacesTrack"), body: t("playbook.surfacesTrackBody"), icon: ClipboardList, tint: "text-warning border-warning/25 bg-warning/10" },
              { eyebrow: "decide", title: t("playbook.surfacesDecide"), body: t("playbook.surfacesDecideBody"), icon: Trophy, tint: "text-violet-700 border-violet-300/40 bg-violet-50" },
              { eyebrow: "see", title: t("playbook.surfacesSee"), body: t("playbook.surfacesSeeBody"), icon: TrendingUp, tint: "text-muted-foreground border-border/60 bg-muted" },
            ].map((tile) => {
              const Icon = tile.icon;
              return (
                <article key={tile.eyebrow} className="flex gap-4 rounded-2xl border border-border/60 bg-card/60 p-5">
                  <span aria-hidden className={`mt-0.5 flex size-10 shrink-0 items-center justify-center rounded-xl border ${tile.tint}`}>
                    <Icon className="size-5" aria-hidden />
                  </span>
                  <div className="min-w-0">
                    <p className="text-sm font-semibold">{tile.title}</p>
                    <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{tile.body}</p>
                  </div>
                </article>
              );
            })}
          </div>
        </section>

        {/* AI rules */}
        <section id="ai" className="mt-14 space-y-6 border-t border-border/50 pt-14">
          <div className="flex flex-wrap items-baseline justify-between gap-3">
            <p className="text-2xs font-semibold uppercase tracking-widest text-primary">{t("playbook.aiEyebrow")}</p>
            <span className="text-2xs tabular-nums text-muted-foreground">04</span>
          </div>
          <h2 className="font-serif text-3xl font-semibold tracking-tight">{t("playbook.aiTitle")}</h2>
          <ul className="grid gap-3 sm:grid-cols-2">
            {[
              t("playbook.aiNever"),
              t("playbook.aiWhiteboard"),
              t("playbook.aiSovereignty"),
              t("playbook.aiTruth"),
            ].map((line, index) => (
              <li key={index} className="flex gap-3 rounded-2xl border border-primary/15 bg-primary/[0.04] p-4 text-sm leading-relaxed text-foreground/90">
                <CheckCircle2 aria-hidden className="mt-0.5 size-4 shrink-0 text-primary" />
                <span>{line}</span>
              </li>
            ))}
          </ul>
        </section>

        {/* Keyboard shortcuts */}
        <section id="keyboard" className="mt-14 space-y-6 border-t border-border/50 pt-14">
          <div className="flex flex-wrap items-baseline justify-between gap-3">
            <p className="text-2xs font-semibold uppercase tracking-widest text-primary">{t("playbook.keyboardEyebrow")}</p>
            <span className="text-2xs tabular-nums text-muted-foreground">05</span>
          </div>
          <h2 className="font-serif text-3xl font-semibold tracking-tight">{t("playbook.keyboardTitle")}</h2>
          <ul className="max-w-2xl space-y-2 text-sm text-foreground/90">
            {[t("playbook.key1"), t("playbook.key2"), t("playbook.key3"), t("playbook.key4")].map((line, index) => (
              <li key={index} className="flex items-center gap-3 rounded-lg border border-border/50 bg-card/60 px-4 py-2 font-mono">
                <Keyboard aria-hidden className="size-4 text-muted-foreground" />
                <span>{line}</span>
              </li>
            ))}
          </ul>
        </section>

        {/* FAQ */}
        <section id="faq" className="mt-14 space-y-6 border-t border-border/50 pt-14">
          <div className="flex flex-wrap items-baseline justify-between gap-3">
            <p className="text-2xs font-semibold uppercase tracking-widest text-primary">{t("playbook.faqEyebrow")}</p>
            <span className="text-2xs tabular-nums text-muted-foreground">06</span>
          </div>
          <h2 className="font-serif text-3xl font-semibold tracking-tight">{t("playbook.faqTitle")}</h2>
          <dl className="max-w-4xl divide-y divide-border/60">
            {[
              [t("playbook.faqQ1"), t("playbook.faqWhat")],
              [t("playbook.faqQ2"), t("playbook.faqWho")],
              [t("playbook.faqQ3"), t("playbook.faqPrice")],
              [t("playbook.faqQ4"), t("playbook.faqOffline")],
              [t("playbook.faqQ5"), t("playbook.faqData")],
              [t("playbook.faqQ6"), t("playbook.faqHuman")],
            ].map(([question, answer], index) => (
              <div key={index} className="space-y-1 py-4">
                <dt className="text-sm font-semibold">{question}</dt>
                <dd className="text-sm leading-relaxed text-muted-foreground">{answer}</dd>
              </div>
            ))}
          </dl>
        </section>

        {/* Colophon */}
        <section id="about" className="mt-14 space-y-4 border-t border-border/50 pt-14">
          <h2 className="font-serif text-2xl font-semibold tracking-tight">{t("playbook.codaTitle")}</h2>
          <p className="max-w-3xl text-base leading-relaxed text-foreground/90">{t("playbook.codaBody")}</p>
          <p className="font-serif text-sm italic text-muted-foreground">{t("playbook.footerSignature")}</p>
          <div className="print:hidden flex flex-wrap items-center gap-3 pt-2">
            <Button variant="outline" size="sm" onClick={print}>
              <Printer aria-hidden className="size-4" />
              <span>{t("playbook.printFromHere")}</span>
            </Button>
            <Button variant="ai" size="sm" asChild className="glow-on-hover">
              <Link href="/register">
                {t("landing.getStarted")}
                <ArrowRight className="size-4" aria-hidden />
              </Link>
            </Button>
          </div>
        </section>
      </main>

      <footer className="border-t border-border/50 py-6 print:hidden">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-2 px-4 text-xs text-muted-foreground">
          <span>AI Career OS — {t("landing.footerNote")}</span>
          <Link href="/" className="hover:text-foreground">← {t("landing.signIn")}</Link>
        </div>
      </footer>
    </div>
  );
}
