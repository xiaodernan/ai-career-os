"use client";

import * as React from "react";
import { ListOrdered } from "lucide-react";
import { useLocale } from "@/lib/i18n/locale-context";
import { cn } from "@/lib/utils";

const CHAPTERS = [
  { href: "#firstweek", titleKey: "playbook.firstweekTitle" },
  { href: "#loop", titleKey: "playbook.loopTitle" },
  { href: "#quickstart", titleKey: "playbook.quickstartTitle" },
  { href: "#surfaces", titleKey: "playbook.surfacesTitle" },
  { href: "#ai", titleKey: "playbook.aiTitle" },
  { href: "#keyboard", titleKey: "playbook.keyboardTitle" },
  { href: "#faq", titleKey: "playbook.faqTitle" },
  { href: "#offer", titleKey: "playbook.offerTitle" },
  { href: "#yearloop", titleKey: "playbook.yearloopTitle" },
  { href: "#manual", titleKey: "playbook.manualInAppTitle" },
  { href: "#keptgoing", titleKey: "playbook.keptGoingTitle" },
  { href: "#gate", titleKey: "playbook.gateTitle" },
  { href: "#about", titleKey: "playbook.colophonTitle" },
] as const;

/**
 * The chapter rail (Epic 236) — the manual's own index.
 *
 * The playbook grew to ten chapters this week, and a reader shouldn't have
 * to skim-scroll a manual that knows what it holds. A compact horizontal
 * rail under the cover: every chapter, one tap away, bilingual by the same
 * table every other surface reads. Static (never sticky), so it cannot
 * fight the page's sticky header; anchor-navigable and focusable.
 */
export function ChapterRail() {
  const { t } = useLocale();
  return (
    <nav aria-label={t("playbook.tocEyebrow")} className="pt-6">
      <div className="flex items-center gap-2 pb-2 text-2xs font-semibold uppercase tracking-widest text-muted-foreground">
        <ListOrdered aria-hidden className="size-3.5" />
        {t("playbook.tocEyebrow")}
      </div>
      <ol className="-mx-1 flex flex-wrap gap-1.5">
        {CHAPTERS.map((chapter, index) => (
          <li key={chapter.href}>
            <a
              href={chapter.href}
              className={cn(
                "inline-flex items-center gap-1.5 rounded-full border border-border/60 bg-card/60 py-1.5 pl-2 pr-3 text-xs text-muted-foreground transition-colors",
                "hover:border-primary/30 hover:text-foreground focus-visible:ring-[3px] focus-visible:ring-primary/30"
              )}
            >
              <span aria-hidden className="text-2xs tabular-nums text-muted-foreground/70">
                {String(index).padStart(2, "0")}
              </span>
              {t(chapter.titleKey)}
            </a>
          </li>
        ))}
      </ol>
    </nav>
  );
}
