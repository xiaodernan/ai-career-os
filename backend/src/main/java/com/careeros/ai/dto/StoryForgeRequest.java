package com.careeros.ai.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/**
 * The story forge request (Epic 274). `rawNote` is the reader's own career note —
 * the only source the verifier trusts — and `locale` tells the engine what language
 * to write in. Absent means English, the product default, like the other editors.
 */
public record StoryForgeRequest(
        @NotBlank @Size(min = 10, max = 12000) String rawNote,
        @Size(max = 8) String locale) {
}
