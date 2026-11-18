package com.careeros.ai.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/**
 * The gap analyst's request (Epic 329). The target role feeds the engine; `locale`
 * tells the editor what language to write in. Optional by contract: absent means
 * English, the product default — exactly like the export and the digest.
 */
public record GapNoteRequest(
        @NotBlank @Size(min = 10, max = 200) String targetRole,
        @Size(max = 80) String seniority,
        @Size(max = 8) String locale) {
}
