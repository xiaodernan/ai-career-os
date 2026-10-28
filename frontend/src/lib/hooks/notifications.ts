"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import { normalizeNotificationInbox } from "@/lib/api/normalize";
import { fail } from "@/lib/hooks/failure";
import { translate } from "@/lib/i18n/locale-context";
import type { NotificationInbox } from "@/lib/api/types";

/**
 * The inbox's writes (roadmap 19.3).
 *
 * Nothing is patched locally: the backend answers every write with the fresh inbox,
 * and that answer replaces the cache. A key that stopped being shown (its episode
 * ended between renders) is dropped by the server, and a local edit would keep
 * painting a row the server refuses to file — so the screen and the record stay the
 * same answer.
 */

/** 19.3 — the items to mark read, written down in one place. */
function markReadBody(keys: string[]): { keys: string[] } {
  return { keys };
}

/** 19.3 — the one item to dismiss. */
function dismissBody(key: string): { key: string } {
  return { key };
}

export function useMarkNotificationsRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (keys: string[]): Promise<NotificationInbox> =>
      normalizeNotificationInbox(
        await api.create<unknown>(endpoints.notificationsRead, markReadBody(keys))
      ),
    onSuccess: (inbox) => qc.setQueryData(["notifications"], inbox),
    onError: fail(translate("notifications.actionFailed") ?? "Couldn't update the inbox."),
  });
}

export function useMarkAllNotificationsRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (): Promise<NotificationInbox> =>
      normalizeNotificationInbox(
        await api.request<unknown>(endpoints.notificationsReadAll, { method: "POST" })
      ),
    onSuccess: (inbox) => qc.setQueryData(["notifications"], inbox),
    onError: fail(translate("notifications.actionFailed") ?? "Couldn't update the inbox."),
  });
}

export function useDismissNotification() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (key: string): Promise<NotificationInbox> =>
      normalizeNotificationInbox(
        await api.create<unknown>(endpoints.notificationsDismiss, dismissBody(key))
      ),
    onSuccess: (inbox) => qc.setQueryData(["notifications"], inbox),
    onError: fail(translate("notifications.actionFailed") ?? "Couldn't update the inbox."),
  });
}
