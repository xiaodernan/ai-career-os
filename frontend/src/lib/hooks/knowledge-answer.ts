"use client";

import { useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { field } from "@/lib/api/body";
import { endpoints } from "@/lib/api/endpoints";
import { fail } from "@/lib/hooks/failure";
import type { RagAnswerResult } from "@/lib/api/types";

/**
 * Ask a grounded question over the reader's OWN ingested evidence.
 *
 * The ai-service runs a bounded StateGraph — retrieve → answer (LLM) → verify
 * (deterministic citation check) → render — so every [n] in the answer points at
 * a quote that was actually retrieved from a ready document. The backend forwards
 * the caller's question under the caller's user id; nothing crosses accounts.
 * `contextSummary` lets the caller add a short in-app hint (e.g. the current page)
 * without crossing the wire with any other user's rows.
 */
export interface RagAnswerInput {
  query: string;
  kinds?: string[];
  documentIds?: string[];
  topK?: number;
  contextSummary?: string;
}

export function useRagAnswer() {
  return useMutation({
    mutationFn: async (input: RagAnswerInput): Promise<RagAnswerResult> =>
      api.create<RagAnswerResult>(endpoints.knowledgeAnswer, {
        query: input.query,
        ...field("kinds", input.kinds),
        ...field("documentIds", input.documentIds),
        ...field("topK", input.topK),
        ...field("contextSummary", input.contextSummary),
      }),
    onError: fail("failures.ragAnswer"),
  });
}
