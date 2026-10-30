"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { authApi } from "@/lib/api/client";
import { tokenStore } from "@/lib/api/token-store";

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
export function useSessions() {
  return useQuery({
    queryKey: ["account", "sessions"],
    queryFn: authApi.listSessions,
  });
}

export function useRevokeSession() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: authApi.revokeSession,
    onSettled: () => qc.invalidateQueries({ queryKey: ["account", "sessions"] }),
  });
}

export function useRevokeAllSessions() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: authApi.revokeAllSessions,
    onSettled: () => qc.invalidateQueries({ queryKey: ["account", "sessions"] }),
  });
}

/**
 * Replacing the password (38.4). Success revokes every refresh token the account holds,
 * so the open-doors list is stale the moment the change lands: the sessions card
 * refetches and tells the truth — no family can refresh any more, including this tab's.
 */
export function useChangePassword() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: authApi.changePassword,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["account", "sessions"] }),
  });
}

/**
 * Erasing the account (38.5). Success is the one moment the local pair must not survive the
 * request that spent it: the rows behind that refresh token are gone, and the access token
 * in memory parses only until its next call answers 404. So the pair and the whole cache
 * are dropped, and the browser leaves through a full document navigation rather than a
 * client route change — the app tree unmounts, no background query refires against the
 * deleted account, and the landing page says the account is gone instead of a 401 bounce.
 */
export function useEraseAccount() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: authApi.eraseAccount,
    onSuccess: () => {
      tokenStore.clear();
      qc.clear();
      window.location.assign("/account-erased");
    },
  });
}
