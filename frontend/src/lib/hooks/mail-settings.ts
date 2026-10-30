"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, request } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import type { MailSettingsRow } from "@/lib/api/types";
import { fail } from "@/lib/hooks/failure";

/**
 * The account's three mail dials, read and settled by the session (42.1, 42.2).
 *
 * The letters carry a signed page, but a reader who deleted every letter -- or who
 * never waited for one -- should not need the mail to change what the mail does. The
 * browser asks the account instead and gets back both the page's address and the
 * state of each dial, so the card can say what is on without opening anything.
 *
 * The write is one dial at a time and the answer is the whole page again, because
 * turning one letter off must not make the card guess what the other two are. The
 * switch moves before the answer arrives -- the reader pressed it, and a switch that
 * waits for a round trip reads as broken -- and a failure puts it back where the
 * account last said it was.
 */

/** The three dials, spelled as the URL segments and the database columns are. */
export type MailDial = "weekly" | "signals" | "reminders";

/** The query the card's switches and the write's answer both live under. */
export const MAIL_SETTINGS_KEY = ["mail", "settings"] as const;

export function fetchMailSettings(): Promise<MailSettingsRow> {
  return api.get<MailSettingsRow>(endpoints.mailSettings);
}

export function useMailSettings() {
  return useQuery({ queryKey: MAIL_SETTINGS_KEY, queryFn: fetchMailSettings });
}

/** One dial, written where the sweeps read it. */
export function setMailDial(list: MailDial, enabled: boolean): Promise<MailSettingsRow> {
  return request<MailSettingsRow>(endpoints.mailSettingsDial(list), {
    method: "PUT",
    body: { enabled },
  });
}

/** The row with one dial moved, named field by field so the type checker sees the union. */
function withDial(row: MailSettingsRow, dial: MailDial, enabled: boolean): MailSettingsRow {
  switch (dial) {
    case "weekly":
      return { ...row, weekly: enabled };
    case "signals":
      return { ...row, signals: enabled };
    case "reminders":
      return { ...row, reminders: enabled };
  }
}

export function useSetMailDial() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ list, enabled }: { list: MailDial; enabled: boolean }) =>
      setMailDial(list, enabled),
    onMutate: async ({ list, enabled }) => {
      await qc.cancelQueries({ queryKey: MAIL_SETTINGS_KEY });
      const previous = qc.getQueryData<MailSettingsRow>(MAIL_SETTINGS_KEY);
      if (previous) qc.setQueryData(MAIL_SETTINGS_KEY, withDial(previous, list, enabled));
      return { previous };
    },
    onError: (err, _dial, ctx) => {
      if (ctx?.previous) qc.setQueryData(MAIL_SETTINGS_KEY, ctx.previous);
      fail("failures.mailSettingSave")(err);
    },
    // The answer is the page as the sweeps will now see it, so the card shows the
    // server's state rather than the optimistic one.
    onSuccess: (fresh) => qc.setQueryData(MAIL_SETTINGS_KEY, fresh),
  });
}
