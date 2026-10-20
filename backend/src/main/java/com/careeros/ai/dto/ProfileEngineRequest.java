package com.careeros.ai.dto;

import jakarta.validation.constraints.Min;

/**
 * The profile-anchored growth engine requests (the story bank and the role
 * suggestions).
 *
 * <p>These two engines ask what the candidate *has*, not what the candidate is
 * aiming at: the story bank reads the profile's own evidence, and the role
 * suggestions read the skills it declares. Neither reads a target role, so
 * neither takes one — a request that names a field the engine ignores is a
 * request that lies about what it asked.
 */
public record ProfileEngineRequest(
        String resumeVersionId,
        /** How many rows the ranker returns; the engine's own default applies otherwise. */
        @Min(1) Integer top) {
}
