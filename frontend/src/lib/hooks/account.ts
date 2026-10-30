"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { authApi } from "@/lib/api/client";

/**
 * Ask for the two letters that move the sign-in address (38.2).
 *
 * Nothing is cached against the answer: the address on `me` stays the old one until the
 * new mailbox confirms (26.2), so a move that cannot have happened yet has nothing to
 * invalidate. The landing page clears the cache when the move actually lands.
 */
export function useRequestEmailChange() {
  return useMutation({ mutationFn: authApi.requestEmailChange });
}

/**
 * The account's open doors (38.3). One query for one card; the list is about live tokens,
 * so it is refetched whenever a close settles — a close that failed because the door was
 * already closed is exactly when the screen's copy is stale.
 */
export const SESSIONS_KEY = ["account", "sessions"] as const;

export function useSessions() {
  return useQuery({ queryKey: SESSIONS_KEY, queryFn: authApi.listSessions });
}

export function useRevokeSession() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: authApi.revokeSession,
    onSettled: () => queryClient.invalidateQueries({ queryKey: SESSIONS_KEY }),
  });
}

export function useRevokeAllSessions() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: authApi.revokeAllSessions,
    onSettled: () => queryClient.invalidateQueries({ queryKey: SESSIONS_KEY }),
  });
}

/**
 * Replacing the password (38.4). Success revokes every refresh token the account holds,
 * so the open-doors list is stale the moment the change lands: the sessions card
 * refetches and tells the truth — no family can refresh any more, including this tab's.
 */
export function useChangePassword() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: authApi.changePassword,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: SESSIONS_KEY }),
  });
}
