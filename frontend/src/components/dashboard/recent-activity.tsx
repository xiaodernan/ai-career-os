"use client";

import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { relativeTime } from "@/lib/format";
import { useLocale } from "@/lib/i18n/locale-context";
import { stageLabel } from "@/lib/pipeline";
import { cn } from "@/lib/utils";
import type { RecentActivityItem } from "@/lib/api/types";

/** A value the backend wrote into the free `payload` map, narrowed to text. */
function text(value: unknown): string | undefined {
  return typeof value === "string" && value.length ? value : undefined;
}

/**
 * One row of the dashboard's "Recent activity" card.
 *
 * The card shows the newest five `application_events` the backend already computes, caches and
 * sends on `DashboardResponse.recentActivity` (`reports/dashboard`). Each row is one event; the
 * sentence is chosen by the event's `kind`, and the words beside it come from that kind's own
 * `payload` keys — `status` carries `{to}`, `note` a `{note}`, `reminder` a `{cleared}` flag,
 * `outcome` a `{field}`, and `reply` a `{subject}`. The mapper passes the map through untouched
 * because its keys have five different writers; this component is the one that owns that
 * vocabulary.
 *
 * A kind this browser does not know yet still gets a row with a neutral sentence. Dropping a real
 * event because the card is behind the server would be a silent loss — the exact shape of the bug
 * this card closes — so the fallback says "an update was logged" instead of filtering the list.
 *
 * Every row with an `applicationId` points at the application behind it; a row cached before that
 * id existed still renders, as text, rather than becoming a link to nowhere.
 */
export interface RecentActivityRowProps {
  row: RecentActivityItem;
}

export function RecentActivityRow({ row }: RecentActivityRowProps) {
  const { t, locale } = useLocale();
  const payload = row.payload ?? {};

  // The five kinds the product actually writes: ApplicationService.writeEvent (status / note /
  // reminder / outcome) and InboundReplyService.file (reply). `default` is the honest stranger.
  let sentence: string;
  let dot: string;
  let stageBadge: string | null = null;

  switch (row.kind) {
    case "status": {
      const to = text(payload.to);
      sentence = t("dashboard.activityStatus");
      dot = "bg-primary";
      stageBadge = to ? stageLabel(t, to) : null;
      break;
    }
    case "note":
      sentence = t("dashboard.activityNote", { note: text(payload.note) ?? "—" });
      dot = "bg-muted-foreground/50";
      break;
    case "reminder":
      sentence =
        payload.cleared === true
          ? t("dashboard.activityReminderCleared")
          : t("dashboard.activityReminderSet");
      dot = "bg-warning";
      break;
    case "outcome":
      sentence =
        text(payload.field) === "offer_compensation"
          ? t("dashboard.activityOutcomeCompensation")
          : text(payload.field) === "rejection_reason"
            ? t("dashboard.activityOutcomeRejection")
            : t("dashboard.activityOutcome");
      dot = "bg-success";
      break;
    case "reply":
      sentence = t("dashboard.activityReply", { subject: text(payload.subject) ?? "—" });
      dot = "bg-primary/70";
      break;
    default:
      sentence = t("dashboard.activityUnknown");
      dot = "bg-muted-foreground/50";
  }

  // The row's own instant, not the payload's reminder time: one clock for every kind, and the
  // record's `createdAt` is the one component guaranteed to be on the wire.
  const when = relativeTime(row.createdAt, locale);
  const inner = (
    <>
      <span className={cn("mt-1.5 size-1.5 shrink-0 rounded-full", dot)} aria-hidden />
      <span className="min-w-0 flex-1">
        <span className="flex items-center gap-2">
          <span className="truncate text-sm font-medium">{sentence}</span>
          {stageBadge ? (
            <Badge variant="outline" className="shrink-0">
              {stageBadge}
            </Badge>
          ) : null}
        </span>
        {when ? <span className="mt-0.5 block text-xs text-muted-foreground">{when}</span> : null}
      </span>
    </>
  );

  return (
    <li className="flex flex-col gap-0.5">
      {row.applicationId ? (
        <Link
          href={`/applications?application=${encodeURIComponent(row.applicationId)}`}
          className="-mx-2.5 flex min-w-0 items-start gap-3 rounded-lg p-2.5 transition-colors duration-150 hover:bg-accent/40 focus-visible:ring-[3px] focus-visible:ring-primary/30"
        >
          {inner}
        </Link>
      ) : (
        <div className="-mx-2.5 flex min-w-0 items-start gap-3 p-2.5">{inner}</div>
      )}
    </li>
  );
}
