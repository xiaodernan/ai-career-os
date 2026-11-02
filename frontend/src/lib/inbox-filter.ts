import type { NotificationItem } from "@/lib/api/types";

/**
 * The kinds the server can put in the inbox, in the backend's own order
 * (`NotificationService.KIND_*`). A kind nobody names here still renders -- it
 * falls back to "Signal" -- but it gets no filter of its own, so this list is the
 * vocabulary the screen claims to speak.
 */
export const INBOX_KINDS = [
  "reminder",
  "stale",
  "ingestion_failed",
  "ingestion_created",
  "saved_search",
  "reply",
] as const;

export type InboxKind = (typeof INBOX_KINDS)[number];

/**
 * A filter read from the address bar. Only a kind the page can name is adopted:
 * a stale bookmark or a typo (`?kind=replied`) shows the whole inbox rather than
 * an empty list that looks like a quiet morning.
 */
export function asInboxKind(raw: string | undefined): InboxKind | null {
  if (!raw) return null;
  return (INBOX_KINDS as readonly string[]).includes(raw) ? (raw as InboxKind) : null;
}

export interface InboxGroup {
  kind: InboxKind;
  count: number;
}

/** The kinds actually present, each with how many rows it holds. */
export function kindsPresent(items: readonly NotificationItem[]): InboxGroup[] {
  return INBOX_KINDS.map((kind) => ({
    kind,
    count: items.filter((item) => item.kind === kind).length,
  })).filter((group) => group.count > 0);
}

/** The rows under a chosen kind; no kind means every row, and unread-only drops the read. */
export function rowsUnder(
  items: readonly NotificationItem[],
  kind: InboxKind | null,
  unreadOnly = false
): NotificationItem[] {
  const filtered = kind == null ? [...items] : items.filter((item) => item.kind === kind);
  return unreadOnly ? filtered.filter((item) => !item.read) : filtered;
}
