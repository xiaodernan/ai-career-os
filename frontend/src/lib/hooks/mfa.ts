"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { mfaApi } from "@/lib/api/client";
import { fail } from "@/lib/hooks/failure";

/**
 * The second door's reads and writes (roadmap 36.4).
 *
 * One query owns the status, and every write invalidates it: activation, a reprint and
 * a turn-off each change what the settings card has to say, and the card is the only
 * reader. Nothing is patched locally -- the answer to a write is a fresh sheet, not a
 * new status, so the status is refetched rather than guessed.
 *
 * The failure sentences are keys: a code the table knows (MFA_INVALID, RATE_LIMITED,
 * MFA_NOT_ENROLLED) speaks its own sentence, and these keys are the fallback for a
 * failure that has none of its own.
 */

export function useMfaStatus() {
  return useQuery({
    queryKey: ["mfa"],
    queryFn: mfaApi.status,
    staleTime: 60_000,
  });
}

export function useEnrollMfa() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: mfaApi.enroll,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["mfa"] }),
    onError: fail("failures.mfaEnroll"),
  });
}

export function useActivateMfa() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: mfaApi.activate,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["mfa"] }),
    onError: fail("failures.mfaActivate"),
  });
}

export function useReissueRecoveryCodes() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: mfaApi.reissueRecoveryCodes,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["mfa"] }),
    onError: fail("failures.mfaRecoveryCodes"),
  });
}

export function useDisableMfa() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: mfaApi.disable,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["mfa"] }),
    onError: fail("failures.mfaDisable"),
  });
}
