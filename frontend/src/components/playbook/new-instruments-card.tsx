"use client";

/**
 * The manual's newest chapter — the three instruments shipped after the atlas was
 * written (Epics 352/353/354). The playbook's own contract is that it describes every
 * surface a reader can stand on; a built feature the manual never mentions is a door
 * the reader cannot know to open. Three static cards, one working door each, all copy
 * through the locale table. No model call, no data fetch — the chapter is a map.
 */

import * as React from "react";
import Link from "next/link";
import { ArrowRight, BookMarked, Eye, Search } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Hint } from "@/components/ui/hint";
import { useLocale } from "@/lib/i18n/locale-context";

const INSTRUMENTS = [
  { icon: BookMarked, titleKey: "playbook.newInstrumentsStoryTitle", bodyKey: "playbook.newInstrumentsStoryBody", ctaKey: "playbook.newInstrumentsCtaTimeline", href: "/timeline", hintKey: "playbook.newInstrumentsHintTimeline" },
  { icon: Search, titleKey: "playbook.newInstrumentsAnswerTitle", bodyKey: "playbook.newInstrumentsAnswerBody", ctaKey: "playbook.newInstrumentsCtaKnowledge", href: "/knowledge", hintKey: "playbook.newInstrumentsHintKnowledge" },
  { icon: Eye, titleKey: "playbook.newInstrumentsLostTitle", bodyKey: "playbook.newInstrumentsLostBody", ctaKey: "playbook.newInstrumentsCtaAdmin", href: "/admin", hintKey: "playbook.newInstrumentsHintAdmin" },
] as const;

export function NewInstrumentsCard() {
  const { t } = useLocale();
  return (
    <ol className="grid gap-3 sm:grid-cols-3">
      {INSTRUMENTS.map((node) => {
        const Icon = node.icon;
        return (
          <li key={node.href}>
            <Card className="h-full">
              <CardContent className="flex h-full flex-col gap-3 p-5">
                <span aria-hidden className="flex size-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <Icon className="size-4" />
                </span>
                <p className="text-sm font-semibold">{t(node.titleKey)}</p>
                <p className="flex-1 text-sm leading-relaxed text-foreground/90">{t(node.bodyKey)}</p>
                <Hint side="bottom" label={t(node.hintKey)}>
                  <Button variant="outline" size="sm" asChild>
                    <Link href={node.href}>
                      {t(node.ctaKey)}
                      <ArrowRight aria-hidden className="size-4" />
                    </Link>
                  </Button>
                </Hint>
              </CardContent>
            </Card>
          </li>
        );
      })}
    </ol>
  );
}
