"use client";

import * as React from "react";
import Link from "next/link";
import { ArrowUpRight, Check, CheckCheck, X } from "lucide-react";
import { PageHeader } from "@/components/common/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { relativeTime } from "@/lib/format";
import { stageLabel } from "@/lib/pipeline";
import { useLocale } from "@/lib/i18n/locale-context";
import {
  useDismissNotification,
  useMarkAllNotificationsRead,
  useMarkNotificationsRead,
} from "@/lib/hooks/notifications";
import { useNotifications } from "@/lib/hooks/resources";
import type { NotificationItem } from "@/lib/api/types";

/**
 * The inbox (roadmap 19.3).
 *
 * Nothing here is a stored notification: each row is a signal the platform already
 * knows about — a reminder that came due, an application that went quiet, a pull the
 * nightly sweep filed — and the row links back to the screen that owns it. The page
 * composes the sentence from the item's kind and its holes, so the wording is the
 * reader's even though the signal is not.
 *
 * Reading and dismissing are the reader's own state, and the backend answers both
 * with the fresh inbox: a row whose episode ended between renders leaves the screen
 * because the server stopped sending it, not because the page guessed.
 */

type Translate = (key: string, vars?: Record<string, string | number>) => string;

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

  const items = inbox.data?.items ?? [];
  const unread = inbox.data?.unread ?? 0;
  const busy = markRead.isPending || markAll.isPending || dismiss.isPending;

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <PageHeader
        title={t("notifications.title")}
        description={t("notifications.description")}
        actions={
          inbox.data ? (
            <div className="flex items-center gap-2">
              <Badge variant={unread > 0 ? "warning" : "outline"}>
                {unread > 0
                  ? t("notifications.unreadBadge", { count: unread })
                  : t("notifications.allRead")}
              </Badge>
              <Button
                size="sm"
                variant="outline"
                loading={markAll.isPending}
                disabled={unread === 0}
                onClick={() => markAll.mutate()}
              >
                <CheckCheck aria-hidden />
                {t("notifications.markAllRead")}
              </Button>
            </div>
          ) : undefined
        }
      />

      <Card>
        <CardContent className="p-6">
          {items.length > 0 ? (
            <ul className="space-y-2">
              {items.map((item) => {
                const name = nameOf(item, t);
                return (
                  <li
                    key={item.key}
                    className="rounded-lg border border-border/70 p-3"
                  >
                    <div className="flex flex-wrap items-start justify-between gap-2">
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
                        {item.note && <p className="text-xs text-danger">{item.note}</p>}
                      </div>
                      <div className="flex shrink-0 items-center gap-1">
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
          ) : inbox.isSuccess ? (
            <div className="space-y-1 py-6 text-center">
              <p className="text-sm font-medium">{t("notifications.empty")}</p>
              <p className="text-xs text-muted-foreground">
                {t("notifications.emptyDescription")}
              </p>
            </div>
          ) : inbox.isError ? (
            <p className="text-sm text-muted-foreground">{t("notifications.unavailable")}</p>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}
