"use client";

import * as React from "react";
import Link from "next/link";
import { ArrowLeft, ArrowRight, Check, Compass, HelpCircle, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { useLocale } from "@/lib/i18n/locale-context";
import { needsQuickStart, markQuickStartSeen } from "@/lib/onboarding";
import { cn } from "@/lib/utils";

/**
 * Epic 347 — the in-app quick start the reader meets on first open.
 *
 * The product teaches in depth (/tour, /playbook, the manual, the nine quests)
 * but nothing walked a NEW reader through the real UI once when they arrived.
 * This is that walk: four short steps, each pointing at a real control and a
 * real route, with Next/Back/Skip. It opens once on first login (persisted via
 * lib/onboarding), and the topbar help button can reopen it through the same
 * custom event, so "read it again" is one click. All copy is locale-keyed.
 */
const STEPS = [
  { icon: Compass, titleKey: "quickstart.step1Title", bodyKey: "quickstart.step1Body", hrefKey: "quickstart.step1Href", hrefLabelKey: "quickstart.step1HrefLabel" },
  { icon: Sparkles, titleKey: "quickstart.step2Title", bodyKey: "quickstart.step2Body", hrefKey: "quickstart.step2Href", hrefLabelKey: "quickstart.step2HrefLabel" },
  { icon: HelpCircle, titleKey: "quickstart.step3Title", bodyKey: "quickstart.step3Body", hrefKey: "quickstart.step3Href", hrefLabelKey: "quickstart.step3HrefLabel" },
  { icon: Check, titleKey: "quickstart.step4Title", bodyKey: "quickstart.step4Body", hrefKey: "quickstart.step4Href", hrefLabelKey: "quickstart.step4HrefLabel" },
] as const;

export const QUICK_START_EVENT = "careeros:open-quick-start";

export function QuickStart() {
  const { t, locale } = useLocale();
  const [open, setOpen] = React.useState(false);
  const [step, setStep] = React.useState(0);

  // Open once on first mount. In SSR the effect runs only in the browser, so the
  // server and first client render agree (no hydration tear).
  React.useEffect(() => {
    if (needsQuickStart()) {
      setStep(0);
      setOpen(true);
    }
  }, []);

  // The topbar help button (and any future "replay" action) can reopen the guide
  // through a plain DOM event — no context provider, no prop drilling.
  React.useEffect(() => {
    const onOpen = () => { setStep(0); setOpen(true); };
    window.addEventListener(QUICK_START_EVENT, onOpen);
    return () => window.removeEventListener(QUICK_START_EVENT, onOpen);
  }, []);

  const close = React.useCallback(() => {
    markQuickStartSeen();
    setOpen(false);
  }, []);

  const next = () => {
    if (step === STEPS.length - 1) {
      close();
    } else {
      setStep((s) => s + 1);
    }
  };

  const current = STEPS[step];
  const Icon = current.icon;

  return (
    <Sheet open={open} onOpenChange={(v) => (v ? setOpen(true) : close())}>
      <SheetContent
        side="right"
        data-testid="quick-start-sheet"
        className="flex w-[min(92vw,440px)] flex-col gap-0 border-l border-border/70 bg-background p-0"
      >
        <SheetHeader className="border-b border-border/60 p-5">
          <div className="flex items-center justify-between">
            <SheetTitle className="font-serif text-xl">{t("quickstart.title")}</SheetTitle>
            <Badge variant="secondary" className="font-normal tabular-nums">
              {t("quickstart.progress", { current: String(step + 1), total: String(STEPS.length) })}
            </Badge>
          </div>
          <SheetDescription>{t("quickstart.description")}</SheetDescription>
        </SheetHeader>

        <div className="flex-1 space-y-4 overflow-y-auto p-5">
          <div
            key={step}
            className="flex gap-3 rounded-xl border border-primary/20 bg-primary/[0.04] p-4 animate-fade-in"
          >
            <span aria-hidden className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <Icon className="size-5" />
            </span>
            <div className="min-w-0 space-y-1.5">
              <p className="text-base font-semibold">{t(current.titleKey)}</p>
              <p className="text-sm leading-relaxed text-muted-foreground">{t(current.bodyKey)}</p>
              <Link
                href={t(current.hrefKey)}
                onClick={close}
                className="inline-flex items-center gap-1.5 rounded-md text-sm font-medium text-primary hover:underline focus-visible:ring-[3px] focus-visible:ring-primary/30"
              >
                {t(current.hrefLabelKey)}
                <ArrowRight aria-hidden className="size-3.5" />
              </Link>
            </div>
          </div>

          <ol className="space-y-1.5" aria-label={t("quickstart.stepsLabel")}>
            {STEPS.map((s, i) => (
              <li key={s.titleKey} className="flex items-center gap-2 text-xs">
                <span
                  aria-hidden
                  className={cn(
                    "flex size-5 shrink-0 items-center justify-center rounded-full border text-2xs tabular-nums",
                    i === step ? "border-primary bg-primary text-primary-foreground"
                      : i < step ? "border-success/40 bg-success/10 text-success"
                      : "border-border text-muted-foreground"
                  )}
                >
                  {i < step ? <Check aria-hidden className="size-3" /> : i + 1}
                </span>
                <span className={cn(i === step ? "font-medium text-foreground" : "text-muted-foreground")}>
                  {t(s.titleKey)}
                </span>
              </li>
            ))}
          </ol>
        </div>

        <div className="flex items-center justify-between gap-2 border-t border-border/60 p-4">
          <Button type="button" variant="ghost" size="sm" onClick={close}>
            {t("quickstart.skip")}
          </Button>
          <div className="flex gap-2">
            {step > 0 && (
              <Button type="button" variant="outline" size="sm" onClick={() => setStep((s) => s - 1)}>
                <ArrowLeft aria-hidden className="size-4" />
                {t("quickstart.back")}
              </Button>
            )}
            <Button type="button" variant="ai" size="sm" onClick={next}>
              {step === STEPS.length - 1 ? t("quickstart.done") : t("quickstart.next")}
              {step === STEPS.length - 1 ? <Check aria-hidden className="size-4" /> : <ArrowRight aria-hidden className="size-4" />}
            </Button>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}
