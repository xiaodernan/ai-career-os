"use client";

import Link from "next/link";

import { useLocale } from "@/lib/i18n/locale-context";
import type { PracticeLine as Practice } from "@/lib/interview-practice";

/**
 * Where this rehearsal sits on its card (59.1, 59.3).
 *
 * The report and the runner both ask the same question -- "is this getting
 * better?" -- so they draw the same sentence from the same fold. A card with a
 * single rehearsal gets the first-of-many sentence; a longer history gets its
 * position and the best graded score, with a door to the list the number came
 * from. `practice` is null for a free rehearsal, and then the line is absent:
 * there is no card to place it on.
 */
export function PracticeLine({
  practice,
  applicationId,
  className,
}: {
  practice: Practice | null;
  applicationId?: string | null;
  className?: string;
}) {
  const { t } = useLocale();
  if (!practice) return null;
  return (
    <p className={`text-xs text-muted-foreground${className ? ` ${className}` : ""}`}>
      {practice.count === 1
        ? t("interviews.practice.first")
        : practice.best != null
          ? t("interviews.practice.progress", {
              position: practice.position,
              count: practice.count,
              best: Math.round(practice.best),
            })
          : t("interviews.practice.progressNoBest", {
              position: practice.position,
              count: practice.count,
            })}{" "}
      {practice.count > 1 && applicationId && (
        <Link
          href={`/interviews?application=${encodeURIComponent(applicationId)}`}
          className="underline underline-offset-2 hover:text-foreground"
        >
          {t("interviews.detail.allInterviews")}
        </Link>
      )}
    </p>
  );
}
