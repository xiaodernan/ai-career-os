package com.careeros.ai.dto;

import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Positive;
import jakarta.validation.constraints.Size;

/**
 * The role-anchored growth engine requests (Epics 10.1-10.13).
 *
 * <p>Each of these engines is one question about the candidate against a target
 * role, and they all anchor on the same two fields: the role being aimed at and
 * the resume version the answer is measured against. The optional fields
 * specialize the question — where to benchmark, which seniority band — and the
 * engine applies its own defaults to whatever is left out.
 *
 * <p>They share one record because they share one shape: a request that named
 * the role, the version and nothing else is the common case, and a record per
 * engine would be nine records that differ by a comment.
 *
 * <p>The two profile-anchored engines — the story bank (6.5) and the role
 * suggestions (10.10) — do not read a target role at all, so they take
 * {@link ProfileEngineRequest} instead. A record that names a field the engine
 * ignores is a request that lies about what it asked.
 */
public record GrowthEngineRequest(
        @NotBlank @Size(min = 10, max = 200) String targetRole,
        @Size(max = 80) String seniority,
        String resumeVersionId,
        @Size(max = 120) String location,
        @Size(min = 3, max = 3) String currency,
        @Positive Integer targetSalary,
        /** How many rows the rankers return; the engine's own default applies otherwise. */
        @Min(1) Integer top) {
}
