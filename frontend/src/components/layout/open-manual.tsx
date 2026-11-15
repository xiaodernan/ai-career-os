"use client";

import * as React from "react";
import { HelpCircle, FileText, Target, TrendingUp, Briefcase, CalendarClock, Feather, Handshake, Mic, MailOpen, Sparkles, BarChart3, Activity, History } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { useLocale } from "@/lib/i18n/locale-context";
import { cn } from "@/lib/utils";

const GROUPS = [
  {
    labelKey: "playbook.surfacesFind",
    routes: [
      { href: "/jobs", icon: Briefcase, labelKey: "nav.jobs", subKey: "navDescriptions.jobs" },
      { href: "/studio", icon: Target, labelKey: "nav.studio", subKey: "navDescriptions.studio" },
      { href: "/copilot", icon: Sparkles, labelKey: "nav.copilot", subKey: "navDescriptions.copilot" },
    ],
  },
  {
    labelKey: "playbook.surfacesPrepare",
    routes: [
      { href: "/resumes", icon: FileText, labelKey: "nav.resumes", subKey: "navDescriptions.resumes" },
      { href: "/knowledge", icon: History, labelKey: "nav.knowledge", subKey: "navDescriptions.knowledge" },
      { href: "/interviews", icon: Mic, labelKey: "nav.interviews", subKey: "navDescriptions.interviews" },
      { href: "/growth", icon: TrendingUp, labelKey: "nav.growth", subKey: "navDescriptions.growth" },
    ],
  },
  {
    labelKey: "playbook.surfacesTrack",
    routes: [
      { href: "/applications", icon: CalendarClock, labelKey: "nav.applications", subKey: "navDescriptions.applications" },
      { href: "/letters", icon: Feather, labelKey: "nav.letters", subKey: "navDescriptions.letters" },
      { href: "/timeline", icon: History, labelKey: "nav.timeline", subKey: "navDescriptions.timeline" },
    ],
  },
  {
    labelKey: "playbook.surfacesDecide",
    routes: [
      { href: "/offers", icon: Handshake, labelKey: "nav.offers", subKey: "navDescriptions.offers" },
      { href: "/replies", icon: MailOpen, labelKey: "nav.replies", subKey: "navDescriptions.replies" },
      { href: "/ceremony", icon: Sparkles, labelKey: "nav.ceremony", subKey: "navDescriptions.ceremony" },
    ],
  },
  {
    labelKey: "playbook.surfacesSee",
    routes: [
      { href: "/analysis", icon: BarChart3, labelKey: "nav.analysis", subKey: "navDescriptions.analysis" },
      { href: "/monitoring", icon: Activity, labelKey: "nav.monitoring", subKey: "navDescriptions.monitoring" },
      { href: "/activity", icon: History, labelKey: "nav.activity", subKey: "navDescriptions.activity" },
    ],
  },
] as const;

export type ManualRoute = (typeof GROUPS)[number]["routes"][number]["href"];

/**
 * The manual, riding along (Epic 239).
 *
 * The product used to have a manual you had to find (/playbook, public but
 * discoverable only). This puts it one tap away, wherever the reader is:
 * the same nine doors the manual draws, in a slide-over, in the reader's
 * language — plus `?` as the anywhere shortcut. The sheet closes on
 * navigation (a link inside it is also a door into the app), and nothing
 * here calls the model or leaves the browser.
 */
export function ManualSheet() {
  const { t } = useLocale();
  const pathname = usePathname();
  const [open, setOpen] = React.useState(false);

  // A link inside the sheet is also a navigation — the panel must not
  // follow the reader across the app afterward.
  const lastPath = React.useRef(pathname);
  React.useEffect(() => {
    if (lastPath.current !== pathname) {
      lastPath.current = pathname;
      setOpen(false);
    }
  }, [pathname]);

  // "?" opens and closes the manual from anywhere the reader is typing into
  // nothing (never inside a field, never with a modifier).
  React.useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key !== "?" || event.ctrlKey || event.metaKey || event.altKey) return;
      const el = event.target;
      if (el instanceof HTMLElement) {
        const tag = el.tagName;
        if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || el.isContentEditable) return;
      }
      event.preventDefault();
      setOpen((current) => !current);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <Button
        variant="ghost"
        size="icon-sm"
        data-testid="manual-open-button"
        aria-label={t("chrome.manualOpen")}
        onClick={() => setOpen(true)}
      >
        <HelpCircle aria-hidden className="size-4" />
      </Button>
      <SheetContent
        side="right"
        data-testid="manual-sheet"
        className="flex w-80 flex-col gap-0 border-l border-border/70 bg-background p-0 sm:w-96"
      >
        <SheetHeader className="border-b border-border/60 p-5">
          <SheetTitle className="font-serif text-xl">{t("chrome.manualTitle")}</SheetTitle>
          <SheetDescription>{t("chrome.manualDescription")}</SheetDescription>
        </SheetHeader>
        <div className="flex-1 overflow-y-auto p-4">
          <nav aria-label={t("chrome.manualTitle")} className="space-y-4">
            {GROUPS.map((group) => (
              <section key={group.labelKey}>
                <p className="mb-1.5 px-1 text-2xs font-semibold uppercase tracking-widest text-muted-foreground">
                  {t(group.labelKey)}
                </p>
                <ul className="space-y-1">
                  {group.routes.map((route) => {
                    const Icon = route.icon;
                    return (
                      <li key={route.href}>
                        <Link
                          href={route.href}
                          className="group flex items-center gap-3 rounded-xl border border-transparent px-2 py-2 transition-colors hover:border-border/60 hover:bg-accent/40 focus-visible:ring-[3px] focus-visible:ring-primary/30"
                        >
                          <span aria-hidden className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary ring-1 ring-inset ring-primary/15 transition-transform duration-200 group-hover:scale-105">
                            <Icon className="size-4" />
                          </span>
                          <span className="min-w-0">
                            <span className="block text-sm font-medium leading-tight">{t(route.labelKey)}</span>
                            <span className="mt-0.5 block truncate text-2xs leading-tight text-muted-foreground">
                              {t(route.subKey)}
                            </span>
                          </span>
                        </Link>
                      </li>
                    );
                  })}
                </ul>
              </section>
            ))}
          </nav>
        </div>
        <div className="border-t border-border/60 p-4">
          <Link
            href="/playbook"
            className={cn(
              "flex items-center justify-center gap-2 rounded-xl border border-primary/20 bg-primary/5 px-4 py-2.5 text-sm font-medium text-primary",
              "transition-colors hover:bg-primary/10 focus-visible:ring-[3px] focus-visible:ring-primary/30"
            )}
          >
            {t("chrome.manualFullLink")}
          </Link>
          <p className="mt-2 text-center text-2xs text-muted-foreground">
            <kbd className="rounded border border-border bg-muted px-1.5 py-0.5 font-sans text-2xs">?</kbd>{" "}
            {t("chrome.manualShortcutHint")}
          </p>
        </div>
      </SheetContent>
    </Sheet>
  );
}
