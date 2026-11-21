package com.careeros.ai.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import java.util.List;

/**
 * A grounded question over the reader's own knowledge base (RAG answer).
 *
 * <p>The wire names here ARE the ai-service's AnswerReq field names — the backend
 * forwards them unchanged under the caller's user id, so a key Jackson drops would
 * be a question the engine never receives. Only `query` is required; the rest narrow
 * which of the caller's evidence the answer may quote.
 */
public record RagAnswerRequest(
        @NotBlank @Size(max = 4000) String query,
        List<String> kinds,
        List<String> documentIds,
        Integer topK,
        String contextSummary) {
}
