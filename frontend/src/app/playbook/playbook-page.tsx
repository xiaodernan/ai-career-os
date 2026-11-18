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
import { ChapterRail } from "@/components/playbook/chapter-rail";
import { FirstWeekGame } from "@/components/playbook/first-week-game";
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
          <h1 className="max-w-4xl text-balance font-serif text-5xl font-semibold leading-[1.08] tracking-tight sm:text-6xl">
            {t("playbook.title")}
          </h1>
          <p className="max-w-3xl text-lg text-muted-foreground">{t("playbook.description")}</p>
          <p className="text-xs uppercase tracking-widest text-muted-foreground">{t("playbook.dateLine")}</p>
        </section>

        {/* The chapter rail — the manual's own index, one tap per door */}
        <ChapterRail />

        {/* Chapter zero — the loop, playable before it is readable */}
        <section id="firstweek" className="mt-14 space-y-6 border-t border-border/50 pt-14">
          <div className="flex flex-wrap items-baseline justify-between gap-3">
            <p className="text-2xs font-semibold uppercase tracking-widest text-primary">{t("playbook.firstweekEyebrow")}</p>
            <span className="text-2xs tabular-nums text-muted-foreground">00</span>
          </div>
          <FirstWeekGame />
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

        {/* The offer chapter */}
        <section id="offer" className="mt-14 space-y-6 border-t border-border/50 pt-14">
          <div className="flex flex-wrap items-baseline justify-between gap-3">
            <p className="text-2xs font-semibold uppercase tracking-widest text-primary">{t("playbook.offerEyebrow")}</p>
            <span className="text-2xs tabular-nums text-muted-foreground">07</span>
          </div>
          <h2 className="font-serif text-3xl font-semibold tracking-tight">{t("playbook.offerTitle")}</h2>
          <p className="max-w-4xl text-base leading-relaxed text-foreground/90">{t("playbook.offerIntro")}</p>
          <ol className="grid gap-3 sm:grid-cols-2">
            {[
              { title: t("playbook.doorShelf"), body: t("playbook.doorShelfBody"), icon: Trophy },
              { title: t("playbook.doorPacket"), body: t("playbook.doorPacketBody"), icon: Printer },
              { title: t("playbook.doorLedger"), body: t("playbook.doorLedgerBody"), icon: BookOpen },
              { title: t("playbook.doorRehearsal"), body: t("playbook.doorRehearsalBody"), icon: Mic },
              { title: t("playbook.doorCommitment"), body: t("playbook.doorCommitmentBody"), icon: ClipboardList },
              { title: t("playbook.doorReview"), body: t("playbook.doorReviewBody"), icon: TrendingUp },
              { title: t("playbook.doorCeremony"), body: t("playbook.doorCeremonyBody"), icon: Sparkles },
            ].map((door, index) => {
              const Icon = door.icon;
              return (
                <li key={index} className="flex gap-4 rounded-2xl border border-border/60 bg-card/60 p-5">
                  <span aria-hidden className="flex size-10 shrink-0 items-center justify-center rounded-xl border border-primary/25 bg-primary/10 text-primary">
                    <Icon className="size-5" aria-hidden />
                  </span>
                  <div className="min-w-0">
                    <p className="text-sm font-semibold">{door.title}</p>
                    <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{door.body}</p>
                  </div>
                </li>
              );
            })}
          </ol>
        </section>

        {/* The year loop — the macro chapter: the arc is a spinner, not a line */}
        <section id="yearloop" className="mt-14 space-y-6 border-t border-border/50 pt-14">
          <div className="flex flex-wrap items-baseline justify-between gap-3">
            <p className="text-2xs font-semibold uppercase tracking-widest text-primary">{t("playbook.yearloopEyebrow")}</p>
            <span className="text-2xs tabular-nums text-muted-foreground">08</span>
          </div>
          <h2 className="font-serif text-3xl font-semibold tracking-tight">{t("playbook.yearloopTitle")}</h2>
          <p className="max-w-4xl text-base leading-relaxed text-foreground/90">{t("playbook.yearloopIntro")}</p>
          <ol className="grid gap-3 sm:grid-cols-3">
            {[
              { title: t("playbook.beatYearOneTitle"), body: t("playbook.beatYearOneBody") },
              { title: t("playbook.beatQuietTitle"), body: t("playbook.beatQuietBody") },
              { title: t("playbook.beatYearTwoTitle"), body: t("playbook.beatYearTwoBody") },
            ].map((beat, index) => (
              <li key={index} className="rounded-2xl border border-border/60 bg-card/60 p-5">
                <p className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
                  {String(index * 4 + 1).padStart(2, "0")} · {beat.title}
                </p>
                <p className="mt-2 text-sm leading-relaxed text-foreground/90">{beat.body}</p>
              </li>
            ))}
          </ol>
          <p className="max-w-4xl text-sm italic leading-relaxed text-muted-foreground">{t("playbook.yearloopClosing")}</p>
        </section>

        {/* The manual, in the app — the last map before the close */}
        <section id="manual" className="mt-14 space-y-6 border-t border-border/50 pt-14">
          <div className="flex flex-wrap items-baseline justify-between gap-3">
            <p className="text-2xs font-semibold uppercase tracking-widest text-primary">{t("playbook.manualInAppEyebrow")}</p>
            <span className="text-2xs tabular-nums text-muted-foreground">09</span>
          </div>
          <h2 className="font-serif text-3xl font-semibold tracking-tight">{t("playbook.manualInAppTitle")}</h2>
          <p className="max-w-4xl text-base leading-relaxed text-foreground/90">{t("playbook.manualInAppIntro")}</p>
          <ol className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {[
              { text: t("playbook.manualInAppOne"), tag: "01" },
              { text: t("playbook.manualInAppTwo"), tag: "02" },
              { text: t("playbook.manualInAppThree"), tag: "03" },
              { text: t("playbook.manualInAppFour"), tag: "04" },
              { text: t("playbook.manualInAppFive"), tag: "05" },
            ].map((door) => (
              <li key={door.tag} className="flex gap-4 rounded-2xl border border-border/60 bg-card/60 p-5">
                <span aria-hidden className="text-2xs tabular-nums font-semibold text-primary">{door.tag}</span>
                <p className="text-sm leading-relaxed text-foreground/90">{door.text}</p>
              </li>
            ))}
          </ol>
          <p className="max-w-4xl text-sm italic leading-relaxed text-muted-foreground">{t("playbook.manualInAppClosing")}</p>
        </section>

        {/* The day you kept going — the third act, before the close */}
        <section id="keptgoing" className="mt-14 space-y-6 border-t border-border/50 pt-14">
          <div className="flex flex-wrap items-baseline justify-between gap-3">
            <p className="text-2xs font-semibold uppercase tracking-widest text-primary">{t("playbook.keptGoingEyebrow")}</p>
            <span className="text-2xs tabular-nums text-muted-foreground">10</span>
          </div>
          <h2 className="font-serif text-3xl font-semibold tracking-tight">{t("playbook.keptGoingTitle")}</h2>
          <p className="max-w-4xl text-base leading-relaxed text-foreground/90">{t("playbook.keptGoingIntro")}</p>
          <ol className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {[
              { title: t("playbook.keptGoingBeatOneTitle"), body: t("playbook.keptGoingBeatOneBody") },
              { title: t("playbook.keptGoingBeatTwoTitle"), body: t("playbook.keptGoingBeatTwoBody") },
              { title: t("playbook.keptGoingBeatThreeTitle"), body: t("playbook.keptGoingBeatThreeBody") },
              { title: t("playbook.keptGoingBeatFourTitle"), body: t("playbook.keptGoingBeatFourBody") },
            ].map((beat, index) => (
              <li key={index} className="rounded-2xl border border-border/60 bg-card/60 p-5">
                <p className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
                  {String(index * 4 + 1).padStart(2, "0")} · {beat.title}
                </p>
                <p className="mt-2 text-sm leading-relaxed text-foreground/90">{beat.body}</p>
              </li>
            ))}
          </ol>
          <p className="max-w-4xl text-sm italic leading-relaxed text-muted-foreground">{t("playbook.keptGoingClosing")}</p>
        </section>

        {/* How the engine thinks — the state graph (Epic 269 in the book) */}
        <section id="stategraph" className="mt-14 space-y-6 border-t border-border/50 pt-14">
          <div className="flex flex-wrap items-baseline justify-between gap-3">
            <p className="text-2xs font-semibold uppercase tracking-widest text-primary">{t("playbook.stategraphEyebrow")}</p>
            <span className="text-2xs tabular-nums text-muted-foreground">11</span>
          </div>
          <h2 className="font-serif text-3xl font-semibold tracking-tight">{t("playbook.stategraphTitle")}</h2>
          <p className="max-w-4xl text-base leading-relaxed text-foreground/90">{t("playbook.stategraphIntro")}</p>
          <ol className="grid gap-3 sm:grid-cols-2">
            {[
              { title: t("playbook.stategraphRetrieveTitle"), body: t("playbook.stategraphRetrieveBody") },
              { title: t("playbook.stategraphDraftTitle"), body: t("playbook.stategraphDraftBody") },
              { title: t("playbook.stategraphVerifyTitle"), body: t("playbook.stategraphVerifyBody") },
              { title: t("playbook.stategraphRenderTitle"), body: t("playbook.stategraphRenderBody") },
            ].map((node, index) => (
              <li key={node.title} className="rounded-2xl border border-border/60 bg-card/60 p-5">
                <p className="text-xs font-semibold uppercase tracking-widest text-primary">
                  {String(index + 1).padStart(2, "0")} · {node.title}
                </p>
                <p className="mt-2 text-sm leading-relaxed text-foreground/90">{node.body}</p>
              </li>
            ))}
          </ol>
          <div className="rounded-2xl border border-border/60 bg-card/60 p-5">
            <p className="text-2xs font-semibold uppercase tracking-widest text-primary">{t("playbook.stategraphRidersTitle")}</p>
            <p className="mt-2 text-sm leading-relaxed text-foreground/90">{t("playbook.stategraphRidersBody")}</p>
          </div>
          <div className="rounded-2xl border border-primary/15 bg-primary/[0.06] p-5">
            <p className="text-2xs font-semibold uppercase tracking-widest text-muted-foreground">{t("playbook.stategraphLedgerTitle")}</p>
            <p className="mt-2 text-sm leading-relaxed text-foreground/90">{t("playbook.stategraphLedgerBody")}</p>
          </div>
          <p className="max-w-4xl text-sm italic leading-relaxed text-muted-foreground">{t("playbook.stategraphClosing")}</p>
        </section>

        {/* The Gate — the whole loop, one page, for the reader about to walk it */}
        <section id="gate" className="mt-14 space-y-6 border-t border-border/50 pt-14">
          <div className="flex flex-wrap items-baseline justify-between gap-3">
            <p className="text-2xs font-semibold uppercase tracking-widest text-primary">{t("playbook.gateEyebrow")}</p>
            <span className="text-2xs tabular-nums text-muted-foreground">12</span>
          </div>
          <h2 className="font-serif text-3xl font-semibold tracking-tight">{t("playbook.gateTitle")}</h2>
          <p className="max-w-4xl text-base leading-relaxed text-foreground/90">{t("playbook.gateIntro")}</p>
          <ol className="grid gap-2">
            {[
              { n: "01", text: t("playbook.gateDoor01") },
              { n: "02", text: t("playbook.gateDoor02") },
              { n: "03", text: t("playbook.gateDoor03") },
              { n: "04", text: t("playbook.gateDoor04") },
              { n: "05", text: t("playbook.gateDoor05") },
              { n: "06", text: t("playbook.gateDoor06") },
              { n: "07", text: t("playbook.gateDoor07") },
              { n: "08", text: t("playbook.gateDoor08") },
              { n: "09", text: t("playbook.gateDoor09") },
              { n: "10", text: t("playbook.gateDoor10") },
              { n: "11", text: t("playbook.gateDoor11") },
            ].map((door, i) => (
              <li key={i} className="flex gap-4 rounded-xl border border-border/60 bg-card/50 px-4 py-3 text-sm leading-relaxed">
                <span aria-hidden className="shrink-0 tabular-nums font-mono text-2xs text-muted-foreground">{door.n}</span>
                <span className="text-foreground/90">{door.text}</span>
              </li>
            ))}
          </ol>
          <p className="max-w-4xl text-sm italic leading-relaxed text-muted-foreground">{t("playbook.gateClosing")}</p>
        </section>

        {/* The Veto — the letter's door that refuses invention (Epic 306) */}
        <section id="veto" className="mt-14 space-y-6 border-t border-border/50 pt-14">
          <div className="flex flex-wrap items-baseline justify-between gap-3">
            <p className="text-2xs font-semibold uppercase tracking-widest text-primary">{t("playbook.vetoEyebrow")}</p>
            <span className="text-2xs tabular-nums text-muted-foreground">13</span>
          </div>
          <h2 className="font-serif text-3xl font-semibold tracking-tight">{t("playbook.vetoTitle")}</h2>
          <p className="max-w-4xl text-base leading-relaxed text-foreground/90">{t("playbook.vetoIntro")}</p>
          <ol className="grid gap-3 sm:grid-cols-2">
            {[
              { title: t("playbook.vetoMindTitle"), body: t("playbook.vetoMindBody") },
              { title: t("playbook.vetoDraftTitle"), body: t("playbook.vetoDraftBody") },
              { title: t("playbook.vetoRenderTitle"), body: t("playbook.vetoRenderBody") },
              { title: t("playbook.vetoYoursTitle"), body: t("playbook.vetoYoursBody") },
            ].map((node, index) => (
              <li key={index} className="rounded-2xl border border-border/60 bg-card/60 p-5">
                <p className="text-xs font-semibold uppercase tracking-widest text-primary">
                  {String(index + 1).padStart(2, "0")} · {node.title}
                </p>
                <p className="mt-2 text-sm leading-relaxed text-foreground/90">{node.body}</p>
              </li>
            ))}
          </ol>
          <p className="max-w-4xl text-sm italic leading-relaxed text-muted-foreground">{t("playbook.vetoClosing")}</p>
        </section>

        {/* The evidence table — this product owns its own numbers (Epic 274) */}
        <section id="inink" className="mt-14 space-y-6 border-t border-border/50 pt-14">
          <div className="flex flex-wrap items-baseline justify-between gap-3">
            <p className="text-2xs font-semibold uppercase tracking-widest text-primary">{t("playbook.inInkEyebrow")}</p>
            <span className="text-2xs tabular-nums text-muted-foreground">14</span>
          </div>
          <h2 className="font-serif text-3xl font-semibold tracking-tight">{t("playbook.inInkTitle")}</h2>
          <p className="max-w-4xl text-base leading-relaxed text-foreground/90">{t("playbook.inInkIntro")}</p>
          <ul className="grid gap-3 sm:grid-cols-2">
            {[
              { num: t("playbook.inInkK1Label"), text: t("playbook.inInkK1Text") },
              { num: t("playbook.inInkK2Label"), text: t("playbook.inInkK2Text") },
              { num: t("playbook.inInkK3Label"), text: t("playbook.inInkK3Text") },
              { num: t("playbook.inInkK4Label"), text: t("playbook.inInkK4Text") },
              { num: t("playbook.inInkK5Label"), text: t("playbook.inInkK5Text") },
              { num: t("playbook.inInkK6Label"), text: t("playbook.inInkK6Text") },
            ].map((row, index) => (
              <li key={index} className="flex items-baseline gap-4 rounded-2xl border border-border/60 bg-card/60 p-5">
                <span className="shrink-0 font-serif text-3xl font-semibold tabular-nums text-primary">{row.num}</span>
                <span className="text-sm leading-relaxed text-foreground/90">{row.text}</span>
              </li>
            ))}
          </ul>
          <p className="max-w-4xl text-2xs leading-relaxed text-muted-foreground">{t("playbook.inInkFootnote")}</p>
        </section>

        {/* The edge of the map — where this product ends and you begin */}
        <section id="edge" className="mt-14 space-y-6 border-t border-border/50 pt-14">
          <div className="flex flex-wrap items-baseline justify-between gap-3">
            <p className="text-2xs font-semibold uppercase tracking-widest text-primary">{t("playbook.edgeEyebrow")}</p>
            <span className="text-2xs tabular-nums text-muted-foreground">15</span>
          </div>
          <h2 className="font-serif text-3xl font-semibold tracking-tight">{t("playbook.edgeTitle")}</h2>
          <p className="max-w-4xl text-base leading-relaxed text-foreground/90">{t("playbook.edgeIntro")}</p>
          <ul className="grid gap-3 sm:grid-cols-2">
            {[
              t("playbook.edgeNot01"),
              t("playbook.edgeNot02"),
              t("playbook.edgeNot03"),
              t("playbook.edgeNot04"),
              t("playbook.edgeNot05"),
              t("playbook.edgeNot06"),
            ].map((line, index) => (
              <li key={index} className="rounded-2xl border border-border/60 bg-card/60 p-5 text-sm leading-relaxed text-foreground/90">
                {line}
              </li>
            ))}
          </ul>
          <p className="max-w-4xl text-sm italic leading-relaxed text-muted-foreground">{t("playbook.edgeClosing")}</p>
        </section>


        {/* Afterward — the one chapter the reader takes with them (Epic 291) */}
        <section id="afterward" className="mt-14 space-y-6 border-t border-border/50 pt-14">
          <div className="flex flex-wrap items-baseline justify-between gap-3">
            <p className="text-2xs font-semibold uppercase tracking-widest text-primary">{t("playbook.afterwardEyebrow")}</p>
            <span className="text-2xs tabular-nums text-muted-foreground">17</span>
          </div>
          <h2 className="font-serif text-3xl font-semibold tracking-tight">{t("playbook.afterwardTitle")}</h2>
          <p className="max-w-4xl text-base leading-relaxed text-foreground/90">{t("playbook.afterwardIntro")}</p>
          <div className="grid gap-3 sm:grid-cols-2">
            {[
              { titleKey: "playbook.afterwardKnockTitle", bodyKey: "playbook.afterwardKnockBody" },
              { titleKey: "playbook.afterwardRehearseTitle", bodyKey: "playbook.afterwardRehearseBody" },
            ].map((node, index) => (
              <div key={index} className="rounded-2xl border border-border/60 bg-card/60 p-5">
                <p className="text-xs font-semibold uppercase tracking-widest text-primary">
                  {String(index + 1).padStart(2, "0")} · {t(node.titleKey)}
                </p>
                <p className="mt-2 text-sm leading-relaxed text-foreground/90">{t(node.bodyKey)}</p>
              </div>
            ))}
          </div>
          <p className="max-w-4xl text-sm leading-relaxed text-foreground/90">{t("playbook.afterwardDaily")}</p>
          <p className="max-w-4xl text-sm italic leading-relaxed text-muted-foreground">{t("playbook.afterwardCarry")}</p>
          <p className="max-w-4xl text-sm leading-relaxed text-muted-foreground">
            {t("playbook.afterwardReturn")}{" "}
            <Link
              href="/dashboard"
              className="font-medium text-primary underline-offset-4 transition-colors hover:text-primary/80 hover:underline"
            >
              {t("playbook.afterwardReturnCta")}
            </Link>
          </p>
        </section>

        {/* Colophon */}

        {/* The ledger watches back — the one chapter about the install itself (Epic 281) */}
        <section id="ledger" className="mt-14 space-y-6 border-t border-border/50 pt-14">
          <div className="flex flex-wrap items-baseline justify-between gap-3">
            <p className="text-2xs font-semibold uppercase tracking-widest text-primary">{t("playbook.ledgerEyebrow")}</p>
            <span className="text-2xs tabular-nums text-muted-foreground">16</span>
          </div>
          <h2 className="font-serif text-3xl font-semibold tracking-tight">{t("playbook.ledgerTitle")}</h2>
          <p className="max-w-4xl text-base leading-relaxed text-foreground/90">{t("playbook.ledgerIntro")}</p>

          {/* The three instruments — one per verb, with the wire each writes. */}
          <ol className="grid gap-3 sm:grid-cols-3">
            {[
              { titleKey: "playbook.ledgerLandTitle", bodyKey: "playbook.ledgerLandBody", wireKey: "playbook.ledgerWireLand" },
              { titleKey: "playbook.ledgerDwellTitle", bodyKey: "playbook.ledgerDwellBody", wireKey: "playbook.ledgerWireDwell" },
              { titleKey: "playbook.ledgerActTitle", bodyKey: "playbook.ledgerActBody", wireKey: "playbook.ledgerWireAct" },
            ].map((node, index) => (
              <li key={index} className="rounded-2xl border border-border/60 bg-card/60 p-5">
                <p className="text-xs font-semibold uppercase tracking-widest text-primary">
                  {String(index + 1).padStart(2, "0")} · {t(node.titleKey)}
                </p>
                <p className="mt-2 text-sm leading-relaxed text-foreground/90">{t(node.bodyKey)}</p>
                <p className="mt-3 font-mono text-2xs text-muted-foreground">{t(node.wireKey)}</p>
              </li>
            ))}
          </ol>

          <div className="rounded-2xl border border-primary/15 bg-primary/[0.06] p-5">
            <p className="text-2xs font-semibold uppercase tracking-widest text-muted-foreground">{t("playbook.ledgerPassphraseTitle")}</p>
            <p className="mt-2 text-sm leading-relaxed text-foreground/90">{t("playbook.ledgerPassphraseBody")}</p>
          </div>
          <div className="rounded-2xl border border-border/60 bg-card/60 p-5">
            <p className="text-2xs font-semibold uppercase tracking-widest text-muted-foreground">{t("playbook.ledgerWeeksTitle")}</p>
            <p className="mt-2 text-sm leading-relaxed text-foreground/90">{t("playbook.ledgerWeeksBody")}</p>
          </div>
          <div className="rounded-2xl border border-border/60 bg-card/60 p-5">
            <p className="text-2xs font-semibold uppercase tracking-widest text-muted-foreground">{t("playbook.ledgerCounselTitle")}</p>
            <p className="mt-2 text-sm leading-relaxed text-foreground/90">{t("playbook.ledgerCounselBody")}</p>
          </div>
          <p className="max-w-4xl text-sm italic leading-relaxed text-muted-foreground">{t("playbook.ledgerFootnote")}</p>
          <div className="print:hidden">
            <Button variant="outline" size="sm" asChild>
              <Link href="/admin">
                {t("playbook.ledgerLink")}
                <ArrowRight aria-hidden className="size-4" />
              </Link>
            </Button>
          </div>
        </section>
        {/* The assistant's first step — the one grounded sentence (Epic 329/331) */}
        <section id="assistant" className="mt-14 space-y-6 border-t border-border/50 pt-14">
          <div className="flex flex-wrap items-baseline justify-between gap-3">
            <p className="text-2xs font-semibold uppercase tracking-widest text-primary">{t("playbook.assistantEyebrow")}</p>
            <span className="text-2xs tabular-nums text-muted-foreground">18</span>
          </div>
          <h2 className="font-serif text-3xl font-semibold tracking-tight">{t("playbook.assistantTitle")}</h2>
          <p className="max-w-4xl text-base leading-relaxed text-foreground/90">{t("playbook.assistantIntro")}</p>
          <ul className="grid gap-3 sm:grid-cols-3">
            {[
              { title: t("playbook.assistantStepTitle"), body: t("playbook.assistantStepBody") },
              { title: t("playbook.assistantEvidenceTitle"), body: t("playbook.assistantEvidenceBody") },
              { title: t("playbook.assistantSilenceTitle"), body: t("playbook.assistantSilenceBody") },
            ].map((item, index) => (
              <li key={index} className="rounded-2xl border border-border/60 bg-card/60 p-5">
                <p className="text-xs font-semibold uppercase tracking-widest text-primary">
                  {String(index + 1).padStart(2, "0")} · {item.title}
                </p>
                <p className="mt-2 text-sm leading-relaxed text-foreground/90">{item.body}</p>
              </li>
            ))}
          </ul>
          <p className="max-w-4xl text-sm italic leading-relaxed text-muted-foreground">{t("playbook.assistantClosing")}</p>
        </section>
        {/* The analyst on the letter — ask-first reading of one inbound letter (Epic 332) */}
        <section id="decode" className="mt-14 space-y-6 border-t border-border/50 pt-14">
          <div className="flex flex-wrap items-baseline justify-between gap-3">
            <p className="text-2xs font-semibold uppercase tracking-widest text-primary">{t("playbook.decodeEyebrow")}</p>
            <span className="text-2xs tabular-nums text-muted-foreground">19</span>
          </div>
          <h2 className="font-serif text-3xl font-semibold tracking-tight">{t("playbook.decodeTitle")}</h2>
          <p className="max-w-4xl text-base leading-relaxed text-foreground/90">{t("playbook.decodeIntro")}</p>
          <ul className="grid gap-3 sm:grid-cols-3">
            {[
              { title: t("playbook.decodeStepTitle"), body: t("playbook.decodeStepBody") },
              { title: t("playbook.decodeNumbersTitle"), body: t("playbook.decodeNumbersBody") },
              { title: t("playbook.decodeSilenceTitle"), body: t("playbook.decodeSilenceBody") },
            ].map((item, index) => (
              <li key={index} className="rounded-2xl border border-border/60 bg-card/60 p-5">
                <p className="text-xs font-semibold uppercase tracking-widest text-primary">
                  {String(index + 1).padStart(2, "0")} · {item.title}
                </p>
                <p className="mt-2 text-sm leading-relaxed text-foreground/90">{item.body}</p>
              </li>
            ))}
          </ul>
          <p className="max-w-4xl text-sm italic leading-relaxed text-muted-foreground">{t("playbook.decodeClosing")}</p>
        </section>

        <section id="about" className="mt-14 space-y-4 border-t border-border/50 pt-14">
          <h2 className="font-serif text-2xl font-semibold tracking-tight">{t("playbook.codaTitle")}</h2>
          <p className="max-w-3xl text-base leading-relaxed text-foreground/90">{t("playbook.codaBody")}</p>
          <p className="font-serif text-sm italic text-muted-foreground">{t("playbook.footerSignature")}</p>
          <p className="print:hidden max-w-3xl text-sm text-muted-foreground">
            {t("playbook.codaLive")}{" "}
            <a
              href="https://xiaodernan.github.io/ai-career-os/showcase.html"
              target="_blank"
              rel="noopener noreferrer"
              className="text-muted-foreground underline underline-offset-4 transition-colors hover:text-foreground"
            >
              {t("playbook.codaLiveCta")}
            </a>
          </p>
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
