"use client";

import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { relativeTime } from "@/lib/format";
import { useLocale } from "@/lib/i18n/locale-context";
import { stageMeta, stageShort } from "@/lib/pipeline";
import { cn } from "@/lib/utils";
import type { AttentionItem } from "@/lib/api/types";

/**
 * One row of the dashboard's "Needs attention" card.
 *
 * A due reminder is the only row with something to do *on* it: the application dialog can move
 * or clear a reminder already, but that means opening the dialog from this card, finding the
 * picker and saving. The two answers a reader of this list actually gives — "not now, tomorrow
 * morning" and "nothing to remember" — belong where the question is asked. Both travel through
 * the same PATCH the dialog uses, so there is one write path, one set of error copy, and one
 * optimistic rollback behind every way of touching a reminder.
 *
 * The buttons sit outside the row's `<Link>`: a press must answer the reminder, not open the
 * application behind it.
 */
export interface AttentionRowProps {
  row: AttentionItem;
  /** True while this row's own write is in flight — the two presses share one mutation. */
  busy?: boolean;
  onSnooze: () => void;
  onClear: () => void;
}

export function AttentionRow({ row, busy = false, onSnooze, onClear }: AttentionRowProps) {
  const { t, locale } = useLocale();
  const meta = stageMeta(row.status ?? "");
  const due = row.reason === "reminder_due";
  // The sentence is the same whether or not the letter's id came along; only its wrapper
  // differs, because a payload without an id has no letter to open.
  const replyLine = row.replyAt
    ? `${t("dashboard.replyWaiting", { when: relativeTime(row.replyAt, locale) })}${
        row.replySubject ? ` · ${row.replySubject}` : ""
      }`
    : null;

  return (
    <li className="flex flex-col gap-0.5">
      <div className="flex items-center gap-1">
        <Link
          href={`/applications?application=${encodeURIComponent(row.id)}`}
          className="-mx-2.5 flex min-w-0 flex-1 items-start gap-3 rounded-lg p-2.5 transition-colors duration-150 hover:bg-accent/40 focus-visible:ring-[3px] focus-visible:ring-primary/30"
        >
          <span
            className={cn(
              "mt-1.5 size-1.5 shrink-0 rounded-full",
              due ? "bg-warning" : "bg-muted-foreground/50"
            )}
            aria-hidden
          />
          <span className="min-w-0 flex-1">
            <span className="flex items-center gap-2">
              <span className="truncate text-sm font-medium">{row.title}</span>
              <Badge variant={meta.badgeVariant} className="shrink-0">
                {stageShort(t, row.status ?? "")}
              </Badge>
            </span>
            <span className="mt-0.5 block truncate text-xs text-muted-foreground">
              {row.companyName ? `${row.companyName} · ` : ""}
              {due && row.reminderAt
                ? t("dashboard.reminderDue", { when: relativeTime(row.reminderAt, locale) })
                : row.updatedAt
                  ? t("dashboard.lastStep", { when: relativeTime(row.updatedAt, locale) })
                  : t("dashboard.noStep")}
            </span>
          </span>
        </Link>
        {/* Only a reminder that has come due can be answered here; a stale row has no reminder to
            move, and offering a "clear" that clears nothing would teach a dead press. */}
        {due ? (
          <span className="flex shrink-0 items-center">
            <Button variant="ghost" size="xs" disabled={busy} onClick={onSnooze}>
              {t("dashboard.snoozeReminder")}
            </Button>
            <Button variant="ghost" size="xs" disabled={busy} onClick={onClear}>
              {t("dashboard.clearReminder")}
            </Button>
          </span>
        ) : null}
      </div>
      {/* The row's reason is the quiet window, but the newest reply is what makes the
          application worth opening: a card that only says "no movement" while a recruiter
          answered yesterday is telling the reader the wrong story.

          The sentence sits outside the application link -- one anchor inside another is not a
          page a browser can build -- and links to the letter itself, so pressing it lands on
          that card on the replies screen rather than on the application behind it. */}
      {row.replyAt ? (
        row.replyId ? (
          <Link
            href={`/replies?mail=${encodeURIComponent(row.replyId)}`}
            className="ml-7 block truncate text-xs text-foreground/80 underline-offset-2 transition-colors hover:text-foreground hover:underline focus-visible:underline"
          >
            {replyLine}
          </Link>
        ) : (
          <span className="ml-7 block truncate text-xs text-foreground/80">{replyLine}</span>
        )
      ) : null}
    </li>
  );
}
