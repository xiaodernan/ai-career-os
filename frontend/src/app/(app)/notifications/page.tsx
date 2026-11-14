"use client";

import * as React from "react";
import Link from "next/link";
import {
  AlertOctagon,
  ArrowUpRight,
  BellRing,
  Check,
  CheckCheck,
  Clock,
  FilePlus2,
  Inbox,
  MoonStar,
  Search,
  Sparkles,
  X,
} from "lucide-react";
import { PageHeader } from "@/components/common/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { EmptyComposition } from "@/components/common/empty-composition";
import { GradientText } from "@/components/ui/gradient-text";
import { reminderPatch, snoozeReminder } from "@/lib/application-edit";
import { relativeTime } from "@/lib/format";
import { asInboxKind, kindsPresent, rowsUnder } from "@/lib/inbox-filter";
import { useUrlState } from "@/lib/hooks/use-url-state";
import { stageLabel } from "@/lib/pipeline";
import { cn } from "@/lib/utils";
import { useLocale } from "@/lib/i18n/locale-context";
import { useUpdateApplication } from "@/lib/hooks/actions";
import {
  useDismissNotification,
  useDismissReadNotifications,
  useMarkAllNotificationsRead,
  useMarkNotificationsRead,
} from "@/lib/hooks/notifications";
import { reminderApplicationId } from "@/lib/notification-reminder";
import { useNotifications } from "@/lib/hooks/resources";
import type { NotificationItem } from "@/lib/api/types";

/**
 * The inbox (roadmap 19.3).
 *
 * Nothing here is a stored notification: each row is a signal the platform already
 * knows about — a reminder that came due, an application that went quiet, a pull the
 * nightly sweep filed, a saved search the board answered — and the row links back to
 * the screen that owns it. The page composes the sentence from the item's kind and its
 * holes, so the wording is the reader's even though the signal is not.
 *
 * Reading and dismissing are the reader's own state, and the backend answers both
 * with the fresh inbox: a row whose episode ended between renders leaves the screen
 * because the server stopped sending it, not because the page guessed.
 *
 * A due reminder is also something to answer, not only to open (roadmap 43.2): the
 * two replies a reader of this list actually gives -- "not now, tomorrow morning"
 * and "nothing to remember" -- are here, next to the row, and travel through the
 * same PATCH the application dialog uses. The application's id is read out of the
 * reminder's key; a key that does not parse has no buttons, because a press that
 * guessed an id would either 404 or edit the wrong application.
 *
 * The rows the reader has already dealt with are also noise to clear in one press
 * (roadmap 45.4): the "Clear read" action files every read row away and leaves the
 * unread ones untouched, so a screen that has been worked through is emptied
 * without hiding anything still waiting. The button is absent when nothing is read,
 * because an action with nothing behind it is a dead button.
 */

type Translate = (key: string, vars?: Record<string, string | number>) => string;

/** The address bar's filter, absent until the reader picks one. */
const VIEW_DEFAULTS: { kind?: string; unread?: boolean } = { kind: undefined, unread: undefined };

const KIND_ICONS: Record<string, React.ComponentType<{ className?: string; "aria-hidden"?: boolean }>> = {
  reminder: Clock,
  stale: MoonStar,
  ingestion_failed: AlertOctagon,
  ingestion_created: FilePlus2,
  saved_search: Search,
  reply: Inbox,
};
const KIND_TINT: Record<string, string> = {
  reminder: "text-warning border-warning/40 bg-warning/10",
  stale: "text-muted-foreground border-border/70 bg-muted",
  ingestion_failed: "text-destructive border-destructive/40 bg-destructive/10",
  ingestion_created: "text-success border-success/40 bg-success/10",
  saved_search: "text-primary border-primary/40 bg-primary/10",
  reply: "text-primary border-primary/40 bg-primary/10",
};

function kindKey(kind: string): string {
  switch (kind) {
    case "reminder":
      return "notifications.kindReminder";
    case "stale":
      return "notifications.kindStale";
    case "ingestion_failed":
      return "notifications.kindIngestionFailed";
    case "ingestion_created":
      return "notifications.kindIngestionCreated";
    case "saved_search":
      return "notifications.kindSavedSearch";
    case "reply":
      return "notifications.kindReply";
    default:
      return "notifications.kindOther";
  }
}

function kindVariant(kind: string): "warning" | "outline" | "destructive" | "success" {
  switch (kind) {
    case "reminder":
      return "warning";
    case "ingestion_failed":
      return "destructive";
    case "ingestion_created":
    case "saved_search":
      return "success";
    default:
      return "outline";
  }
}

/** The item's name for aria labels and fallbacks; an item without one is still an item. */
function nameOf(item: NotificationItem, t: Translate): string {
  if (item.kind === "ingestion_failed" || item.kind === "ingestion_created") {
    return item.title || t("notifications.unnamedFeed");
  }
  if (item.kind === "saved_search") {
    return item.title || t("notifications.unnamedSearch");
  }
  return item.title || t("notifications.untitled");
}

function lineOf(item: NotificationItem, t: Translate): string {
  const title = nameOf(item, t);
  switch (item.kind) {
    case "reminder":
      return t("notifications.reminderLine", { title });
    case "stale":
      return t("notifications.staleLine", { title });
    case "ingestion_failed":
      return t("notifications.ingestionFailedLine", { feed: title });
    case "ingestion_created":
      return t("notifications.ingestionCreatedLine", {
        feed: title,
        count: item.count ?? 0,
      });
    case "saved_search":
      return t("notifications.savedSearchLine", {
        name: title,
        count: item.count ?? 0,
      });
    case "reply":
      return t("notifications.replyLine", { title });
    default:
      return item.title || t("notifications.fallbackLine");
  }
}

export default function NotificationsPage() {
  const { t, locale } = useLocale();
  const inbox = useNotifications();
  const markRead = useMarkNotificationsRead();
  const markAll = useMarkAllNotificationsRead();
  const dismiss = useDismissNotification();
  const clearRead = useDismissReadNotifications();
  const settleReminder = useUpdateApplication();
  const [view, setView] = useUrlState<{ kind?: string; unread?: boolean }>(VIEW_DEFAULTS, {
    booleanKeys: ["unread"],
  });
  const kind = asInboxKind(view.kind);
  const unreadOnly = view.unread === true;

  const items = React.useMemo(() => inbox.data?.items ?? [], [inbox.data?.items]);
  const rows = React.useMemo(() => rowsUnder(items, kind, unreadOnly), [items, kind, unreadOnly]);
  const kindGroups = React.useMemo(() => kindsPresent(items), [items]);
  const unread = inbox.data?.unread ?? 0;
  /** The rows the reader has dealt with: the inbox it is showing, minus the unread. */
  const read = Math.max(0, items.length - unread);
  const busy =
    markRead.isPending ||
    markAll.isPending ||
    dismiss.isPending ||
    clearRead.isPending ||
    settleReminder.isPending;

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      {/* The inbox is the second screen a signed-in reader opens after the dashboard -- it is the
          one the unread badge pulls them back to. It carries the same front-door band the
          dashboard and the auth door established: a static light-theme wash, a dark-only aurora
          (screen-blend over a light Card would wash it white), a shimmer hairline and CSS-only
          staggered entrance. The blobs are plain spans and the accent is a plain span, so the
          band adds zero client JS and leaves the route budget untouched. Every motion layer is
          decorative; `prefers-reduced-motion` stays authoritative via globals.css. */}
      <section className="animate-fade-up relative overflow-hidden rounded-2xl border hairline bg-card/60 shadow-card">
        {/* Light-theme ambient washes: static gradients, zero per-frame cost. */}
        <div
          aria-hidden
          className="pointer-events-none absolute -right-20 -top-24 h-64 w-64 rounded-full"
          style={{
            background:
              "radial-gradient(closest-side, color-mix(in oklch, var(--primary) 16%, transparent), transparent)",
          }}
        />
        <div
          aria-hidden
          className="pointer-events-none absolute -bottom-28 -left-24 h-64 w-64 rounded-full"
          style={{
            background:
              "radial-gradient(closest-side, color-mix(in oklch, var(--primary) 9%, transparent), transparent)",
          }}
        />
        {/* Dark-theme aurora: screen-blend light only ever composited over a dark surface. */}
        <div aria-hidden className="pointer-events-none absolute inset-0 hidden overflow-hidden dark:block">
          <span className="aurora-blob aurora-blob-1 opacity-30" />
          <span className="aurora-blob aurora-blob-2 opacity-30" />
          <div className="aurora-grid opacity-30" />
        </div>
        {/* Shimmer hairline crowns the band -- the same premium separator the dashboard uses. */}
        <span aria-hidden className="shimmer-rule absolute inset-x-0 top-0 block h-px" />
        <div className="relative px-6 py-6">
          <PageHeader
            title={<GradientText className="italic">{t("notifications.title")}</GradientText>}
            description={
              <span className="animate-fade-up block" style={{ animationDelay: "90ms" }}>
                {t("notifications.description")}
              </span>
            }
            actions={
              inbox.data ? (
                <div className="animate-fade-up flex flex-wrap items-center gap-2" style={{ animationDelay: "160ms" }}>
                  <Badge variant={unread > 0 ? "warning" : "outline"}>
                    {unread > 0
                      ? t("notifications.unreadBadge", { count: unread })
                      : t("notifications.allRead")}
                  </Badge>
                  <Button
                    size="sm"
                    variant="outline"
                    className="glow-on-hover"
                    loading={markAll.isPending}
                    disabled={unread === 0}
                    onClick={() => markAll.mutate()}
                  >
                    <CheckCheck aria-hidden />
                    {t("notifications.markAllRead")}
                  </Button>
                  {read > 0 ? (
                    <Button
                      size="sm"
                      variant="ghost"
                      loading={clearRead.isPending}
                      onClick={() => clearRead.mutate()}
                    >
                      {t("notifications.clearRead")}
                      <span className="text-xs text-muted-foreground">{read}</span>
                    </Button>
                  ) : null}
                </div>
              ) : undefined
            }
          />
        </div>
      </section>

      <Card>
        <CardContent className="p-6">
          {items.length > 0 ? (
            <>
              {/* One kind at a time (45.2), and the unread ones alone (45.3): the inbox
                  holds six kinds of signal, and a reader looking for one of them should
                  not have to read the other five. Only the kinds actually present get a
                  chip, and the address bar keeps the choice so a reload lands on the
                  same view. */}
              <div
                className="mb-4 flex flex-wrap items-center gap-1.5"
                role="group"
                aria-label={t("notifications.filterByKind")}
              >
                <Button
                  size="sm"
                  variant={kind === null && !unreadOnly ? "secondary" : "ghost"}
                  aria-pressed={kind === null && !unreadOnly}
                  onClick={() => setView({ kind: undefined, unread: undefined })}
                >
                  {t("notifications.filterAll")}
                </Button>
                {kindGroups.map((group) => (
                  <Button
                    key={group.kind}
                    size="sm"
                    variant={kind === group.kind ? "secondary" : "ghost"}
                    aria-pressed={kind === group.kind}
                    onClick={() => setView({ kind: group.kind })}
                  >
                    {t(kindKey(group.kind))}
                    <span className="text-xs text-muted-foreground">{group.count}</span>
                  </Button>
                ))}
                <Button
                  size="sm"
                  variant={unreadOnly ? "secondary" : "ghost"}
                  aria-pressed={unreadOnly}
                  disabled={unread === 0 && !unreadOnly}
                  className="ml-auto"
                  onClick={() => setView({ unread: !unreadOnly })}
                >
                  {t("notifications.filterUnread")}
                  <span className="text-xs text-muted-foreground">{unread}</span>
                </Button>
              </div>
              {rows.length > 0 ? (
                <ul className="space-y-2">
                  {rows.map((item) => {
                    const name = nameOf(item, t);
                    const applicationId =
                      item.kind === "reminder" ? reminderApplicationId(item.key) : null;
                    const Icon = KIND_ICONS[item.kind] ?? BellRing;
                    return (
                      <li
                        key={item.key}
                        className={cn(
                          "group rounded-lg border p-3 transition-all duration-150 hover:-translate-y-0.5 hover:shadow-soft",
                          item.read
                            ? "border-border/70 hover:border-border"
                            : "border-primary/25 bg-primary/[0.04] hover:border-primary/40",
                        )}
                      >
                        <div className="flex flex-wrap items-start justify-between gap-2">
                          <div className="flex min-w-0 items-start gap-3">
                            <span
                              aria-hidden
                              className={cn(
                                "mt-0.5 flex size-9 shrink-0 items-center justify-center rounded-lg border transition-transform duration-200 group-hover:scale-105",
                                KIND_TINT[item.kind] ??
                                  "text-muted-foreground border-border/60 bg-muted",
                              )}
                            >
                              <Icon className="size-4" aria-hidden />
                            </span>
                            <div className="min-w-0 space-y-1">
                              <div className="flex flex-wrap items-center gap-2">
                              <Badge variant={kindVariant(item.kind)}>
                                {t(kindKey(item.kind))}
                              </Badge>
                              {!item.read && (
                                <span
                                  className="size-1.5 rounded-full bg-primary"
                                  aria-hidden
                                />
                              )}
                              {item.status &&
                                (item.kind === "reminder" || item.kind === "stale") && (
                                  <span className="text-xs text-muted-foreground">
                                    {stageLabel(t, item.status)}
                                  </span>
                                )}
                              <span className="text-xs text-muted-foreground">
                                {relativeTime(item.at, locale)}
                              </span>
                            </div>
                            <p className="text-sm">{lineOf(item, t)}</p>
                            {item.subject && (
                              <p className="text-xs text-muted-foreground">{item.subject}</p>
                            )}
                            {item.note && (
                              <p className="text-xs text-danger">{item.note}</p>
                            )}
                            </div>
                          </div>
                          <div className="flex shrink-0 items-center gap-0.5">
                            {/* The reminder's two answers (43.2). The clear travels through the same
                                picker-shaped patch as the dialog: emptying a reminder is spelled as
                                an explicit command there, and this page must not invent a second
                                spelling of it. */}
                            {applicationId && (
                              <>
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  disabled={busy}
                                  onClick={() =>
                                    settleReminder.mutate({
                                      id: applicationId,
                                      patch: { reminderAt: snoozeReminder() },
                                    })
                                  }
                                >
                                  {t("notifications.snoozeReminder")}
                                </Button>
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  disabled={busy}
                                  onClick={() =>
                                    settleReminder.mutate({
                                      id: applicationId,
                                      patch: reminderPatch(item.at, ""),
                                    })
                                  }
                                >
                                  {t("notifications.clearReminder")}
                                </Button>
                              </>
                            )}
                            {item.link && (
                              <Button asChild size="sm" variant="ghost">
                                <Link
                                  href={item.link}
                                  aria-label={t("notifications.openAria", { title: name })}
                                >
                                  <ArrowUpRight aria-hidden />
                                  {t("notifications.open")}
                                </Link>
                              </Button>
                            )}
                            {!item.read && (
                              <Button
                                size="icon-sm"
                                variant="ghost"
                                disabled={busy}
                                aria-label={t("notifications.markReadAria", { title: name })}
                                onClick={() => markRead.mutate([item.key])}
                              >
                                <Check aria-hidden />
                              </Button>
                            )}
                            <Button
                              size="icon-sm"
                              variant="ghost"
                              disabled={busy}
                              aria-label={t("notifications.dismissAria", { title: name })}
                              onClick={() => dismiss.mutate(item.key)}
                            >
                              <X aria-hidden />
                            </Button>
                          </div>
                        </div>
                      </li>
                    );
                  })}
                </ul>
              ) : (
                <p className="py-6 text-center text-sm text-muted-foreground">
                  {t("notifications.filterEmpty")}
                </p>
              )}
            </>
          ) : inbox.isSuccess ? (
            <EmptyComposition
              icon={<Sparkles aria-hidden />}
              promise={t("notifications.allCaughtUpTitle")}
              title={t("notifications.empty")}
              description={t("notifications.allCaughtUpDescription")}
              className="py-8"
            />
          ) : inbox.isError ? (
            <p className="text-sm text-muted-foreground">{t("notifications.unavailable")}</p>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}
