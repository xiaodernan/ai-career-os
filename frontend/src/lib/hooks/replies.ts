"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import { field } from "@/lib/api/body";
import { normalizePage, str } from "@/lib/api/normalize";
import { translate } from "@/lib/i18n/locale-context";
import { fail } from "@/lib/hooks/failure";
import type { InboundLinkRow, InboundMail, Page } from "@/lib/api/types";

/**
 * The replies surface (37.4): the address the settings card hands out, the letters the
 * replies page lists, and the one write that files a waiting letter on a card.
 *
 * The reading is the server's, not a guess made here: `intent`, `company`, `role` and
 * `suggestedStage` arrive already decided (or null, which means "not read yet"), and the
 * mapper only copies them. A field this file invented would paint a badge over a letter
 * nobody read.
 */

/** One letter, read under the names `InboundMailDtos.InboundMailItem` spells. */
export function mapInboundMail(raw: unknown): InboundMail {
  return {
    id: str(raw, "id") ?? "",
    fromAddress: str(raw, "fromAddress") ?? "",
    subject: str(raw, "subject") ?? "",
    bodyText: str(raw, "bodyText") ?? "",
    intent: str(raw, "intent") ?? null,
    company: str(raw, "company") ?? null,
    role: str(raw, "role") ?? null,
    suggestedStage: str(raw, "suggestedStage") ?? null,
    applicationId: str(raw, "applicationId") ?? null,
    applicationTitle: str(raw, "applicationTitle") ?? null,
    receivedAt: str(raw, "receivedAt") ?? null,
    filedAt: str(raw, "filedAt") ?? null,
  };
}

/** The account's letters, newest first, one page at a time (37.3's list route). */
export function useInboundMails(params?: { page?: number; size?: number }) {
  return useQuery({
    queryKey: ["inbound", "mails", params],
    queryFn: async (): Promise<Page<InboundMail>> =>
      normalizePage(
        await api.get<unknown>(endpoints.inboundMails, { size: 50, ...(params ?? {}) }),
        mapInboundMail
      ),
  });
}

/**
 * The address a recruiter's reply is forwarded to.
 *
 * A deployment without a receiving domain answers 503 `INBOUND_NOT_CONFIGURED`, which is
 * not an outage: the card reads that code and says the inbox does not exist rather than
 * offering a retry that would fail the same way.
 */
export function useInboundLink() {
  return useQuery({
    queryKey: ["inbound", "link"],
    queryFn: async (): Promise<InboundLinkRow> => {
      const raw = await api.get<unknown>(endpoints.inboundLink);
      return { address: str(raw, "address") ?? "" };
    },
    retry: false,
  });
}

/**
 * File one waiting letter on the card it answers.
 *
 * The letter is the one that moves, never the card: this write adds the timeline row the
 * server owns and nothing else. A second call on the same card is the server's no-op, and
 * a different card is refused (409), so the cache is only ever replaced by the answer.
 */
export function useFileInboundMail() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, applicationId }: { id: string; applicationId: string }) =>
      mapInboundMail(
        await api.create<unknown>(endpoints.inboundMailFile(id), field("applicationId", applicationId))
      ),
    onSuccess: (mail) => {
      qc.invalidateQueries({ queryKey: ["inbound"] });
      // Filing turns a waiting letter into a bell episode, so the count has to be re-read.
      qc.invalidateQueries({ queryKey: ["notifications"] });
      if (mail.applicationId) {
        qc.invalidateQueries({ queryKey: ["application", mail.applicationId, "events"] });
      }
      toast.success(translate("replies.filedToast"));
    },
    onError: fail("replies.fileFailed"),
  });
}
