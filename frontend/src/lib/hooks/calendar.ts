"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import type { CalendarLinkRow } from "@/lib/api/types";

/**
 * The account's calendar subscription address (34.1).
 *
 * The browser asks the backend to sign an address; it never fetches the feed itself.
 * That is the point of the address: a calendar app holds no session, so the URL is
 * the credential, and the only job this side has is to put the signed string where
 * the reader can copy it. Re-signing is cheap and stateless, so the query is cached
 * for the life of the tab rather than persisted.
 */

export function fetchCalendarLink(): Promise<CalendarLinkRow> {
  return api.get<CalendarLinkRow>(endpoints.calendarLink);
}

export function useCalendarLink() {
  return useQuery({ queryKey: ["calendar", "link"], queryFn: fetchCalendarLink });
}
