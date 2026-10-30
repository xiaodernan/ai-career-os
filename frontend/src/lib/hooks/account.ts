"use client";

import { useMutation } from "@tanstack/react-query";
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
