"use client";

import { Globe } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useLocale } from "@/lib/i18n/locale-context";
import { cn } from "@/lib/utils";

/**
 * The language switch, on its own.
 *
 * The sidebar carries one for the signed-in app, but the two surfaces an
 * anonymous visitor can reach -- the auth pages and the 404 -- are not in
 * the shell, so they had no switch at all. That is the worst place to
 * leave one: a reader who cannot read the page is also the reader who
 * cannot find the control that would fix it.
 *
 * So the switch is a component of its own, and the sidebar's button and
 * this one are the same component with the same labels -- which is also
 * what makes the end-to-end suite's job possible: it drives the sidebar's
 * copy and this one has to answer the same way.
 */
export function LocaleSwitcher({
  className,
  showLabel = true,
}: {
  className?: string;
  /** The collapsed sidebar shows the globe alone; the icon is the whole button. */
  showLabel?: boolean;
}) {
  const { locale, setLocale, t } = useLocale();
  const toChinese = locale === "en";

  return (
    <Button
      type="button"
      variant="ghost"
      size="sm"
      onClick={() => setLocale(toChinese ? "zh" : "en")}
      aria-label={toChinese ? t("chrome.switchToChinese") : t("chrome.switchToEnglish")}
      className={cn("text-muted-foreground", className)}
    >
      <Globe aria-hidden />
      {showLabel && (toChinese ? "中文" : "EN")}
    </Button>
  );
}
