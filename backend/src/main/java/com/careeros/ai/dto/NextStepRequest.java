package com.careeros.ai.dto;

import jakarta.validation.constraints.Size;

/**
 * The next-step request (Epic 331). No body is required — the client says only what
 * language to answer in; the backend owns every other fact the editor reads.
 */
public record NextStepRequest(
        @Size(max = 8) String locale) {
}
