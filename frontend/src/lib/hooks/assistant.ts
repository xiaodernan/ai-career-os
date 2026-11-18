import { useMutation } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import type { NextStep } from "@/lib/api/types";
import { fail } from "@/lib/hooks/failure";

/**
 * Epic 331 — the assistant's one proactive first step.
 *
 * The dashboard shows the numbers already; this asks the editor for the one
 * sentence the reader can act on before anything else. No request is made
 * until the reader asks for one — the assistant never speaks unasked.
 */
export function useNextStep() {
  return useMutation({
    mutationFn: async (input: { locale?: string }) =>
      (await api.create<unknown>(endpoints.assistantNextStep, input)) as NextStep,
    onError: fail("failures.nextStep"),
  });
}
