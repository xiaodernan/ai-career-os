"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import type { MailSettingsRow } from "@/lib/api/types";

/**
 * The account's three mail dials, asked for by the session (42.1).
 *
 * The letters carry a signed page, but a reader who deleted every letter -- or who
 * never waited for one -- should not need the mail to change what the mail does. The
 * browser asks the account instead and gets back both the page's address and the
 * state of each dial, so the card can say what is on without opening anything.
 */

export function fetchMailSettings(): Promise<MailSettingsRow> {
  return api.get<MailSettingsRow>(endpoints.mailSettings);
}

export function useMailSettings() {
  return useQuery({ queryKey: ["mail", "settings"], queryFn: fetchMailSettings });
}
