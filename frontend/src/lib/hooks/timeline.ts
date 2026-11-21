import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import { fail } from "@/lib/hooks/failure";
import { useLocale } from "@/lib/i18n/locale-context";
import { list, str } from "@/lib/api/normalize";
import type { TimelineEntry } from "@/lib/api/types";

/**
 * The timeline the loop already wrote (Epic 81): one ordered list of the dated
 * facts this account is made of. The backend collects the rows it owns —
 * applications, notes, contacts, resume versions, matches and rehearsals — and
 * the ai-service merges them deterministically; this hook only reads the
 * answer. No window (the list is capped server-side), no cursor, no filter: the
 * timeline is the one screen where scrolling past your own history is the whole
 * question.
 */
export function useTimeline() {
  return useQuery({
    queryKey: ["timeline"],
    queryFn: async (): Promise<TimelineEntry[]> =>
      list(await api.get<unknown>(endpoints.timeline), "timeline").map(mapTimelineEntry),
  });
}

/**
 * Epic 345 — one grounded story over the timeline the reader already sees. The
 * events are sent by the page (no new DB read); a silent relay answers a null
 * narrative, which the card renders as an honest "nothing to tell" rather than
 * a generic pep talk.
 */
export function useCareerNarrative() {
  const { locale } = useLocale();
  return useMutation({
    mutationFn: async (events: TimelineEntry[]): Promise<{ narrative?: string | null }> =>
      (await api.create<{ narrative?: string | null }>(endpoints.timelineNarrative, {
        events,
        locale,
      })) ?? {},
    onError: fail("failures.careerNarrative"),
  });
}

function mapTimelineEntry(raw: unknown): TimelineEntry {
  return {
    at: str(raw, "at") ?? "",
    kind: str(raw, "kind") ?? "unknown",
    title: str(raw, "title") ?? "",
    refId: str(raw, "refId", "ref_id") ?? "",
    summary: str(raw, "summary") ?? "",
  };
}
